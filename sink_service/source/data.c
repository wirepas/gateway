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

/**********************************************************************
 *                   DBUS Methods implementation                      *
 **********************************************************************/
/**
 * \brief   Send a message handler
 * \param   ... (from sd_bus function signature)
 */
static int send_message(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    app_message_t message;
    app_res_e res;
    const void * data;
    size_t n;
    int r;
    uint8_t qos;

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

    LOGD("Message to send on EP %d from EP %d to 0x%x size = %d\n",
         message.dst_ep,
         message.src_ep,
         message.dst_addr,
         message.num_bytes);

    /* Send packet. For now, packets are not tracked to keep behavior simpler */
    message.pdu_id = 0;
    message.on_data_sent_cb = NULL;

    res = WPC_send_data_with_options(&message);
    if (res != APP_RES_OK)
    {
        LOGE("Cannot send data: %d\n", res);
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
                           uint8_t num_bytes,
                           app_addr_t src_addr,
                           app_addr_t dst_addr,
                           app_qos_e qos,
                           uint8_t src_ep,
                           uint8_t dst_ep,
                           uint32_t travel_time,
                           uint8_t hop_count,
                           unsigned long long timestamp_ms)
{
    sd_bus_message * m = NULL;
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

    /* Release message to free memory */
    sd_bus_message_unref(m);

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

int Data_Init(sd_bus * bus, char * object, char * interface)
{
    int ret;

    m_bus = bus;
    m_object = object;
    m_interface = interface;

    /* Register for data on all EP (EP 0 to 255) */
    for (uint16_t i = 0; i <= 255; i++)
    {
        WPC_register_for_data(i, onDataReceived);
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
