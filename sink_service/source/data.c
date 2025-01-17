/* Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
 *
 * See file LICENSE for full license details.
 *
 */
#include <stdio.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdbool.h>
#include <errno.h>
#include <time.h>

#include "data.h"
#include "wpc.h"

#define LOG_MODULE_NAME "Data"
#define MAX_LOG_LEVEL INFO_LOG_LEVEL
#include "logger.h"

/** Bus instance received at init and needed to send signals */
static sd_bus * m_bus = NULL;

/** Object received at init and needed to send signals */
static char * m_object = NULL;

/** Interface received at init and needed to send signals */
static char * m_interface = NULL;

/** Bus slot used to register the Vtable */
static sd_bus_slot * m_slot = NULL;

/** Max mtu size of sink */
static size_t m_max_mtu;

/* Max number of downlink packet being sent in parallel */
static size_t m_downlink_limit;

/**********************************************************************
 *                   DBUS Methods implementation                      *
 **********************************************************************/

static uint8_t m_message_queued_in_sink = 0;

static void on_data_sent_cb(uint16_t pduid, uint32_t buffering_delay, uint8_t result)
{
    m_message_queued_in_sink -= (uint8_t) (pduid >> 8);
    LOGD("Message sent %d, Message_queued: %d\n", pduid, m_message_queued_in_sink);
}

/**
 * \brief   Send a message handler
 * \param   ... (from sd_bus function signature)
 */
static int send_message(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    static uint8_t m_pdu_id = 0;

    app_message_t message;
    app_res_e res;
    const void * data;
    size_t n;
    int r;
    uint8_t qos;
    uint8_t weight;

    /* Read the parameters */
    r = sd_bus_message_read(m,
                            "uyyuyby",
                            &message.dst_addr,
                            &message.src_ep,
                            &message.dst_ep,
                            &message.buffering_delay,
                            &qos,
                            &message.is_unack_csma_ca,
                            &message.hop_limit);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Fail to parse parameters: %s\n", strerror(-r));
        return r;
    }

    /* Update QoS Enum field (in case app_qos_e is encoded on more than 1 byte) */
    message.qos = qos;

    r = sd_bus_message_read_array(m, 'y', &data, &n);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Fail to parse data: %s\n", strerror(-r));
        return r;
    }

    /* Update the data fields */
    message.bytes = data;
    message.num_bytes = n;

    if (m_downlink_limit > 0)
    {
        /* Check if message can be queued */
        weight = (n + m_max_mtu - 1) / m_max_mtu;
        if (m_message_queued_in_sink + weight > m_downlink_limit)
        {
            // No point to try sending data, queue is already full
            return sd_bus_reply_method_return(m, "u", APP_RES_OUT_OF_MEMORY);
        }

        /* Keep track of packet queued on the sink */
        /* Encode weight in ID */
        message.pdu_id = weight << 8 | m_pdu_id++;
        message.on_data_sent_cb = on_data_sent_cb;
    }
    else
    {
        message.pdu_id = 0;
        message.on_data_sent_cb = NULL;

    }

    LOGD("Message to send on EP %d from EP %d to 0x%x size = %d\n",
         message.dst_ep,
         message.src_ep,
         message.dst_addr,
         message.num_bytes);



    res = WPC_send_data_with_options(&message);
    if (res != APP_RES_OK)
    {
        LOGE("Cannot send data: %d\n", res);
    }
    else if (m_downlink_limit > 0)
    {
        m_message_queued_in_sink += weight;
        LOGI("Message_queued: %d\n", m_message_queued_in_sink);
    }

    return sd_bus_reply_method_return(m, "u", res);
}

/**********************************************************************
 *                        C-mesh api callbacks                        *
 **********************************************************************/
/**
 * \brief  Called when a message is received from serial interface
 * \param   ... (from c-mesh api headers)
 */
static bool onDataReceived(const uint8_t * bytes,
                           size_t num_bytes,
                           app_addr_t src_addr,
                           app_addr_t dst_addr,
                           app_qos_e qos,
                           uint8_t src_ep,
                           uint8_t dst_ep,
                           uint32_t travel_time,
                           uint8_t hop_count,
                           unsigned long long timestamp_ms)
{
    __attribute__((cleanup(sd_bus_message_unrefp))) sd_bus_message *m = NULL;
    int r;

    LOGD("%llu -> Data received on EP %d of len %d from 0x%x to 0x%x\n",
         timestamp_ms,
         dst_ep,
         num_bytes,
         src_addr,
         dst_addr);

    /* Create a new signal to be generated on Dbus */
    r = sd_bus_message_new_signal(m_bus, &m, m_object, m_interface, "MessageReceived");

    if (r < 0)
    {
        LOGE("Cannot create signal error=%s\n", strerror(-r));
        return false;
    }

    /* Load all parameters */
    // clang-format off
    r = sd_bus_message_append(m,
                              "tuuyyuyy",
                              timestamp_ms,
                              src_addr,
                              dst_addr,
                              src_ep,
                              dst_ep,
                              travel_time,
                              qos,
                              hop_count);
    // clang-format on
    if (r < 0)
    {
        LOGE("Cannot append info error=%s\n", strerror(-r));
        return false;
    }

    r = sd_bus_message_append_array(m, 'y', bytes, num_bytes);
    if (r < 0)
    {
        LOGE("Cannot append array error=%s\n", strerror(-r));
        return false;
    }

    /* Send the signal on bus */
    sd_bus_send(m_bus, m, NULL);

    return true;
}

/**********************************************************************
 *                   VTABLE for data module                           *
 **********************************************************************/
static const sd_bus_vtable data_vtable[] = {
    SD_BUS_VTABLE_START(0),

    /* Method to send data */
    /* Parameters are:
     *  u -> dst_addr
     *  y -> src_ep
     *  y -> dst_ep
     *  u -> buffering_delay
     *  y -> qos
     *  b -> is_unack_csma_ca
     *  y -> hop_limit
     *  ay -> byte array
     */
    SD_BUS_METHOD("SendMessage", "uyyuybyay", "u", send_message, SD_BUS_VTABLE_UNPRIVILEGED),

    /* Signal generated on message received */
    /* Parameters are:
     *  t -> timestamp_ms
     *  u -> src_addr
     *  u -> dst_addr
     *  y -> src_ep
     *  y -> dst_ep
     *  u -> travel_time
     *  y -> qos
     *  y -> hop_count
     *  ay -> byte array
     */
    SD_BUS_SIGNAL("MessageReceived", "tuuyyuyyay", 0),

    SD_BUS_VTABLE_END};

int Data_Init(sd_bus * bus, char * object, char * interface, size_t downlink_limit)
{
    int ret;

    m_bus = bus;
    m_object = object;
    m_interface = interface;
    m_downlink_limit = downlink_limit;

    /* Register for all data */
    WPC_register_for_data(onDataReceived);

    if (WPC_get_mtu((uint8_t *) &m_max_mtu) != APP_RES_OK)
    {
        LOGW("Cannot read max mtu from node");
        m_max_mtu = 102;
    }

    /* Install the data vtable */
    ret = sd_bus_add_object_vtable(bus, &m_slot, object, interface, data_vtable, NULL);
    if (ret < 0)
    {
        LOGE("Failed to issue method call: %s\n", strerror(-ret));
        return ret;
    }

    return 0;
}

void Data_Close()
{
    if (m_slot != NULL)
    {
        sd_bus_slot_unref(m_slot);
    }
}
