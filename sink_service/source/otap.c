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

#include "otap.h"
//TODO: must be splitted in config and error
#include "config_macros.h"
#include "wpc.h"

#define LOG_MODULE_NAME "Otap"
#define MAX_LOG_LEVEL DEBUG_LOG_LEVEL
#include "logger.h"

/** Structure to hold unmodifiable configs from node */
typedef struct
{
    uint32_t stored_len;
    uint32_t processed_len;
    uint32_t firmware_area_id;
    uint16_t stored_crc;
    uint16_t processed_crc;
    uint8_t stored_status;
    uint8_t stored_type;
    uint8_t stored_seq;
    uint8_t processed_seq;
} sink_otap_t;

/** Sink static values read at init time */
static sink_otap_t m_sink_otap;

/** Bus instance received at init and needed to send signals */
static sd_bus * m_bus = NULL;

/** Object received at init and needed to send signals */
static char * m_object = NULL;

/** Interface received at init and needed to send signals */
static char * m_interface = NULL;

/** Bus slot used to register the Vtable */
static sd_bus_slot * m_slot = NULL;

static bool initialize_unmodifiable_variables();

/**********************************************************************
 *                   DBUS Methods implementation                      *
 **********************************************************************/

/**
 * \brief   Upload local scratchpad
 * \param   ... (from sd_bus function signature)
 */
static int upload_scratchpad(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    app_res_e res;
    const void * data;
    size_t n;
    int r;
    uint8_t seq;

    /* Read the parameters (seq of scratchpad)*/
    r = sd_bus_message_read(m, "y", &seq);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Fail to parse parameters: %s\n", strerror(-r));
        return r;
    }

    r = sd_bus_message_read_array(m, 'y', &data, &n);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Fail to parse data: %s\n", strerror(-r));
        return r;
    }

    LOGD("Upload scratchpad: with seq %d of size %d\n", seq, n);

    /* Send the file to the sink */
    res = WPC_upload_local_scratchpad(n, (uint8_t *) data, seq);
    if (res != APP_RES_OK)
    {
        LOGE("Cannot upload local scratchpad\n");
        SET_WPC_ERROR(error, "WPC_update_local_scratchpad", res);
        return -EINVAL;
    }

    /* New scratchpad uploaded, update parameters values exposed on bus */
    initialize_unmodifiable_variables();

    /* Do some sanity check: Do not generate error for that */
    if (m_sink_otap.stored_len != n)
    {
        LOGE("Scratchpad is not loaded correctly (wrong size) %d vs %d\n",
             m_sink_otap.stored_len,
             n);
    }

    if (m_sink_otap.stored_seq != seq)
    {
        LOGE("Wrong seq number after loading a scratchpad image \n");
    }

    /* Reply with the response */
    return sd_bus_reply_method_return(m, "");
}

/**
 * \brief   Update local scratchpad
 * \param   ... (from sd_bus function signature)
 */
static int process_scratchpad(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    app_res_e res;

    res = WPC_update_local_scratchpad();
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_update_local_scratchpad", res);
        return -EINVAL;
    }

    /* Node must be rebooted to process the scratchpad */
    res = WPC_stop_stack();
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_stop_stack", res);
        return -EINVAL;
    }

    /* Read back the variables after the restart */
    initialize_unmodifiable_variables();

    /* Reply with the response */
    return sd_bus_reply_method_return(m, "");
}

/**
 * \brief   Get target scratchpad and action handler
 * \param   ... (from sd_bus function signature)
 */
static int get_target_scratchpad(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    int r;
    app_res_e res;
    uint8_t target_seq;
    uint16_t target_crc;
    uint8_t action;
    uint8_t param;

    sd_bus_message * reply = NULL;

    res = WPC_read_target_scratchpad(&target_seq, &target_crc, &action, &param);
    if (res != APP_RES_OK)
    {
        LOGE("Cannot read target scratchpad\n");
        SET_WPC_ERROR(error, "WPC_read_target_scratchpad", res);
        return -EINVAL;
    }

    /* Create the answer */
    r = sd_bus_message_new_method_return(m, &reply);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Cannot create new message return %s\n", strerror(-r));
        return r;
    }

    r = sd_bus_message_append(reply, "yqyy", target_seq, target_crc, action, param);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Cannot append parameters: %s\n", strerror(-r));
        return r;
    }

    return sd_bus_send(NULL, reply, NULL);
}

/**
 * \brief   Set target scratchpad and action handler
 * \param   ... (from sd_bus function signature)
 */
static int set_target_scratchpad(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    uint8_t target_seq;
    uint16_t target_crc;
    uint8_t action;
    uint8_t param;
    int r;
    app_res_e res;

    /* Read the parameters */
    r = sd_bus_message_read(m, "yqyy", &target_seq, &target_crc, &action, &param);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Fail to parse parameters: %s\n", strerror(-r));
        return r;
    }

    res = WPC_write_target_scratchpad(target_seq, target_crc, action, param);
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_write_target_scratchpad", res);
        return -EINVAL;
    }

    /* Reply with the response */
    return sd_bus_reply_method_return(m, "b", true);
}

/**********************************************************************
 *                   VTABLE for otap module                         *
 **********************************************************************/
// clang-format off
static const sd_bus_vtable otap_vtable[] =
{
    SD_BUS_VTABLE_START(0),

    /* Read only parameters backup-ed with a table (Read each time stack starts) */
    SD_BUS_PROPERTY("StoredLen",       "u", NULL, offsetof(sink_otap_t, stored_len), 0),
    SD_BUS_PROPERTY("StoredCrc",       "q", NULL, offsetof(sink_otap_t, stored_crc), 0),
    SD_BUS_PROPERTY("StoredSeq",       "y", NULL, offsetof(sink_otap_t, stored_seq), 0),
    SD_BUS_PROPERTY("StoredStatus",    "y", NULL, offsetof(sink_otap_t, stored_status), 0),
    SD_BUS_PROPERTY("StoredType",      "y", NULL, offsetof(sink_otap_t, stored_type), 0),
    SD_BUS_PROPERTY("ProcessedLen",    "u", NULL, offsetof(sink_otap_t, processed_len), 0),
    SD_BUS_PROPERTY("ProcessedCrc",    "q", NULL, offsetof(sink_otap_t, processed_crc), 0),
    SD_BUS_PROPERTY("ProcessedSeq",    "y", NULL, offsetof(sink_otap_t, processed_seq), 0),
    SD_BUS_PROPERTY("FirmwareAreaId",  "u", NULL, offsetof(sink_otap_t, firmware_area_id), 0),

    /* Methods related to config */
    SD_BUS_METHOD("ProcessScratchpad",  "", "", process_scratchpad, SD_BUS_VTABLE_UNPRIVILEGED),
    /* Parameters are:
     *  y -> sequence
     *  ay -> byte array containing the scratchpad to upload
     */
    SD_BUS_METHOD("UploadScratchpad","yay", "", upload_scratchpad, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("SetTargetScratchpad","yqyy", "b", set_target_scratchpad, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetTargetScratchpad", "", "yqyy", get_target_scratchpad, SD_BUS_VTABLE_UNPRIVILEGED),

    SD_BUS_VTABLE_END
};
// clang-format on

static bool initialize_unmodifiable_variables()
{
    app_scratchpad_status_t status;
    if (WPC_get_local_scratchpad_status(&status) != APP_RES_OK)
    {
        LOGE("Cannot get local scratchpad status\n");
        return false;
    }

    m_sink_otap.stored_len = status.scrat_len;
    m_sink_otap.stored_crc = status.scrat_crc;
    m_sink_otap.stored_seq = status.scrat_seq_number;

    m_sink_otap.stored_status = status.scrat_status;
    m_sink_otap.stored_type = status.scrat_type;

    m_sink_otap.processed_len = status.processed_scrat_len;
    m_sink_otap.processed_crc = status.processed_scrat_crc;
    m_sink_otap.processed_seq = status.processed_scrat_seq_number;

    m_sink_otap.firmware_area_id = status.firmware_memory_area_id;

    return true;
}

int Otap_Init(sd_bus * bus, char * object, char * interface)
{
    int r;

    m_bus = bus;
    m_object = object;
    m_interface = interface;

    /* Read unmodifiable config from sink */
    initialize_unmodifiable_variables();

    /* Install the config vtable */
    r = sd_bus_add_object_vtable(bus, &m_slot, object, interface, otap_vtable, &m_sink_otap);

    if (r < 0)
    {
        LOGE("Fail to issue method call: %s\n", strerror(-r));
        return r;
    }

    return 0;
}

void Otap_Close()
{
    if (m_slot != NULL)
    {
        sd_bus_slot_unref(m_slot);
    }
}
