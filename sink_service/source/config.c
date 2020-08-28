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

#include "config.h"
#include "config_macros.h"
#include "wpc.h"

#define LOG_MODULE_NAME "Config"
#define MAX_LOG_LEVEL DEBUG_LOG_LEVEL
#include "logger.h"

/** Structure to hold unmodifiable configs from node */
typedef struct
{
    uint16_t stack_profile;
    uint16_t hw_magic;
    uint16_t ac_range_min;
    uint16_t ac_range_max;
    uint16_t app_config_max_size;
    uint16_t version[4];
    uint8_t max_mtu;
    uint8_t ch_range_min;
    uint8_t ch_range_max;
    uint8_t pdu_buffer_size;
} sink_config_t;

/** Sink static values read at init time */
static sink_config_t m_sink_config;

/** Bus instance received at init and needed to send signals */
static sd_bus * m_bus = NULL;

/** Object received at init and needed to send signals */
static char * m_object = NULL;

/** Interface received at init and needed to send signals */
static char * m_interface = NULL;

/** Bus slot used to register the Vtable */
static sd_bus_slot * m_slot = NULL;

/**********************************************************************
 *               DBUS Property handler definition (R/W)               *
 **********************************************************************/
/*
 *  Generic read/write handlers
 */
HANDLER_READ_UINT8(node_role, WPC_get_role)
HANDLER_WRITE_UINT8(node_role, WPC_set_role)

HANDLER_READ_UINT8(network_channel, WPC_get_network_channel)
HANDLER_WRITE_UINT8(network_channel, WPC_set_network_channel)

HANDLER_READ_UINT8(sink_cost, WPC_get_sink_cost)
HANDLER_WRITE_UINT8(sink_cost, WPC_set_sink_cost)

HANDLER_READ_UINT32(channel_map, WPC_get_channel_map)
HANDLER_WRITE_UINT32(channel_map, WPC_set_channel_map)

HANDLER_READ_UINT8(stack_status, WPC_get_stack_status)

HANDLER_READ_UINT16(current_ac, WPC_get_current_access_cycle)

HANDLER_READ_UINT32(node_add, WPC_get_node_address)
HANDLER_WRITE_UINT32(node_add, WPC_set_node_address)

HANDLER_READ_UINT32(network_add, WPC_get_network_address)
HANDLER_WRITE_UINT32(network_add, WPC_set_network_address)

HANDLER_READ_BOOL(cipher_key, WPC_is_cipher_key_set)
HANDLER_READ_BOOL(authen_key, WPC_is_authentication_key_set)

/**
 * \brief   Read channel map
 *          It is a wrapper on top of default reader to avoid
 *          doing the call over dual mcu api for nothing.
 * \param   ... (from sd_bus property handler)
 */
static int channel_map_read_handler_wrapper(sd_bus * bus,
                                            const char * path,
                                            const char * interface,
                                            const char * property,
                                            sd_bus_message * reply,
                                            void * userdata,
                                            sd_bus_error * error)
{
    if (m_sink_config.version[0] >= 4)
    {
        LOGD("No need to ask channel map if stack >= 4\n");
        SET_WPC_ERROR(error, "WPC_get_channel_map", APP_RES_ATTRIBUTE_NOT_SET);
        return -EINVAL;
    }
    else
    {
        return channel_map_read_handler(bus, path, interface, property, reply, userdata, error);
    }
}
/**
 * \brief   Get firmware version
 * \param   ... (from sd_bus property handler)
 */
static int get_firmware_version(sd_bus * bus,
                                const char * path,
                                const char * interface,
                                const char * property,
                                sd_bus_message * reply,
                                void * userdata,
                                sd_bus_error * error)
{
    int r;
    r = sd_bus_message_append_array(reply,
                                    'q',
                                    m_sink_config.version,
                                    sizeof(m_sink_config.version));

    LOGD("Version Firmware is %d.%d.%d.%d\n",
         m_sink_config.version[0],
         m_sink_config.version[1],
         m_sink_config.version[2],
         m_sink_config.version[3]);

    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Cannot append array: %s\n", strerror(-r));
        return r;
    }

    return 0;
}

/**
 * \brief   Get current min ac range
 * \param   ... (from sd_bus property handler)
 */
static int cur_ac_range_handler(sd_bus * bus,
                                const char * path,
                                const char * interface,
                                const char * property,
                                sd_bus_message * reply,
                                void * userdata,
                                sd_bus_error * error)
{
    uint16_t min, max, ret;
    app_res_e res = WPC_get_access_cycle_range(&min, &max);

    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_get_access_cycle_range", res);
        LOGE("Cannot get access cycle range (ret=%d)\n", res);
        return -EINVAL;
    }
    else
    {
        if (strcmp(property, "ACRangeMinCur") == 0)
        {
            ret = min;
        }
        else
        {
            ret = max;
        }
        sd_bus_message_append(reply, "q", ret);
        return 0;
    }
}

/**
 * \brief   Read key handler. As key cannot be read back,
 *          just return table of 0xff
 * \param   ... (from sd_bus property handler)
 */
static int read_key(sd_bus * bus,
                    const char * path,
                    const char * interface,
                    const char * property,
                    sd_bus_message * reply,
                    void * userdata,
                    sd_bus_error * error)
{
    uint8_t key[16];
    // Key cannot be read back
    memset(key, 0xff, 16);
    sd_bus_message_append_array(reply, 'y', key, sizeof(key));
    return 0;
}

typedef app_res_e (*set_key_f)(uint8_t key[16]);

/**
 * \brief   Global function to set a key (cipher or authen)
 * \param   value
 *          The message received on dbus containing the key
 * \param   key_set_function
 *          The WPC key function to use
 * \return  Return code of operation
 */
static app_res_e set_key(sd_bus_message * value, set_key_f key_set_function)
{
    const void * key;
    app_res_e res = APP_RES_INTERNAL_ERROR;
    size_t n;
    int r;

    r = sd_bus_message_read_array(value, 'y', &key, &n);
    if ((r < 0) || (n != 16))
    {
        LOGE("Cannot get key from request %s len=%d\n", strerror(-r), n);
        return res;
    }

    res = (key_set_function)((uint8_t *) key);
    return res;
}

/**
 * \brief   Set cipher key handler
 * \param   ... (from sd_bus property handler)
 */
static int set_cipher_key(sd_bus * bus,
                          const char * path,
                          const char * interface,
                          const char * property,
                          sd_bus_message * value,
                          void * userdata,
                          sd_bus_error * error)
{
    app_res_e res;

    res = set_key(value, WPC_set_cipher_key);
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_set_cipher_key", res);
        return -EINVAL;
    }

    return 0;
}

/**
 * \brief   Set authentication key handler
 * \param   ... (from sd_bus property handler)
 */
static int set_authen_key(sd_bus * bus,
                          const char * path,
                          const char * interface,
                          const char * property,
                          sd_bus_message * value,
                          void * userdata,
                          sd_bus_error * error)
{
    app_res_e res;
    res = set_key(value, WPC_set_authentication_key);
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_set_authentication_key", res);
        return -EINVAL;
    }

    return 0;
}

/**********************************************************************
 *                   DBUS Methods implementation                      *
 **********************************************************************/

/**
 * \brief   Internal wrapper to send a dbus signal
 * \param   name
 *          Name of the signal to generate
 * \return  True if signal is correctly sent, false otherwise
 */
static bool send_dbus_signal(const char * name)
{
    /* Create a new signal to be generated on Dbus */
    sd_bus_message * m = NULL;
    int r = sd_bus_message_new_signal(m_bus, &m, m_object, m_interface, name);

    if (r < 0)
    {
        LOGE("Cannot create signal error=%s\n", strerror(-r));
        return false;
    }

    /* Send the signal on bus */
    r = sd_bus_send(m_bus, m, NULL);
    if (r < 0)
    {
        LOGE("Cannot send signal error=%s\n", strerror(-r));
        sd_bus_message_unref(m);
        return false;
    }

    /* Release message to free memory */
    sd_bus_message_unref(m);

    return true;
}

/**
 * \brief   Set stack state
 * \param   ... (from sd_bus function signature)
 */
static int set_stack_state(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    app_res_e res;
    bool state;
    int r;

    /* Read the parameters */
    r = sd_bus_message_read(m, "b", &state);
    if (r < 0)
    {
        LOGE("Fail to parse parameters: %s\n", strerror(-r));
        sd_bus_error_set_errno(error, EINVAL);
        return r;
    }

    if (state)
    {
        res = WPC_start_stack();
        WPC_set_autostart(1);
        if (res == APP_RES_OK)
        {
            LOGD("Stack started manually\n");
            send_dbus_signal("StackStarted");
        }
    }
    else
    {
        WPC_set_autostart(0);
        res = WPC_stop_stack();
    }

    if (res != APP_RES_OK)
    {
        LOGE("Set stack state (%d) res = %d\n", state, res);
    }

    /* Reply with the response */
    return sd_bus_reply_method_return(m, "b", res == APP_RES_OK);
}

/**
 * \brief   Clear cipher key
 * \param   ... (from sd_bus function signature)
 */
static int clear_cipher_key(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    app_res_e res = WPC_remove_cipher_key();
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_remove_cipher_key", res);
        return -EINVAL;
    }
    // No return code
    return sd_bus_reply_method_return(m, "");
}

/**
 * \brief   Clear authentication key
 * \param   ... (from sd_bus function signature)
 */
static int clear_authen_key(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    app_res_e res = WPC_remove_authentication_key();
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_remove_authentication_key", res);
        return -EINVAL;
    }

    // No return code
    return sd_bus_reply_method_return(m, "");
}

/** \brief  Maximum reserved size for app config */
#define MAX_APP_CONFIG_SIZE 128

/**
 * \brief   Get app config handler
 * \param   ... (from sd_bus function signature)
 */
static int get_app_config(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    int r;
    app_res_e res;
    uint8_t seq;
    uint16_t interval;
    uint8_t app_config[MAX_APP_CONFIG_SIZE];
    uint8_t size;

    sd_bus_message * reply = NULL;

    res = WPC_get_app_config_data_size(&size);
    if (res != APP_RES_OK)
    {
        LOGE("Cannot determine app config size\n");
        SET_WPC_ERROR(error, "WPC_get_app_config_data_size", res);
        return -EINVAL;
    }

    if (size > MAX_APP_CONFIG_SIZE)
    {
        LOGE("App config size too big compared to reserved buffer\n");
        sd_bus_error_set_errno(error, ENOMEM);
        return -ENOMEM;
    }

    res = WPC_get_app_config_data(&seq, &interval, app_config, size);
    if (res != APP_RES_OK)
    {
        LOGE("Cannot get app config\n");
        SET_WPC_ERROR(error, "WPC_get_app_config_data", res);
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

    r = sd_bus_message_append(reply, "yq", seq, interval);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Cannot append parameters: %s\n", strerror(-r));
        return r;
    }

    r = sd_bus_message_append_array(reply, 'y', app_config, size);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Cannot append array: %s\n", strerror(-r));
        return r;
    }

    return sd_bus_send(NULL, reply, NULL);
}

/**
 * \brief   Set app config handler
 * \param   ... (from sd_bus function signature)
 */
static int set_app_config(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    uint8_t seq;
    uint16_t interval;
    const void * app_config;
    size_t n;
    int r;
    app_res_e res;

    /* Read the parameters */
    r = sd_bus_message_read(m, "yq", &seq, &interval);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Fail to parse parameters: %s\n", strerror(-r));
        return r;
    }

    r = sd_bus_message_read_array(m, 'y', &app_config, &n);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Fail to parse app config bytes: %s\n", strerror(-r));
        return r;
    }

    res = WPC_set_app_config_data(seq, interval, (uint8_t *) app_config, n);
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_set_app_config_data", res);
        return -EINVAL;
    }

    /* Reply with the response */
    return sd_bus_reply_method_return(m, "b", true);
}

/**
 * \brief   Set current ac range
 * \param   ... (from sd_bus function signature)
 */
static int set_ac_range(sd_bus_message * m, void * userdata, sd_bus_error * error)
{
    uint16_t min, max;
    int r;
    app_res_e res;

    /* Read the parameters */
    r = sd_bus_message_read(m, "qq", &min, &max);
    if (r < 0)
    {
        sd_bus_error_set_errno(error, r);
        LOGE("Fail to parse parameters: %s\n", strerror(-r));
        return r;
    }

    res = WPC_set_access_cycle_range(min, max);
    if (res != APP_RES_OK)
    {
        SET_WPC_ERROR(error, "WPC_set_access_cycle_range", res);
        return -EINVAL;
    }

    /* Reply with the response */
    return sd_bus_reply_method_return(m, "b", true);
}

/**********************************************************************
 *                   VTABLE for config module                         *
 **********************************************************************/
static const sd_bus_vtable config_vtable[] = {
    SD_BUS_VTABLE_START(0),

    /* Read only parameters backup-ed with a table (Read at boot up) */
    SD_BUS_PROPERTY("StackProfile", "q", NULL, offsetof(sink_config_t, stack_profile), 0),
    SD_BUS_PROPERTY("HwMagic", "q", NULL, offsetof(sink_config_t, hw_magic), 0),
    SD_BUS_PROPERTY("MaxMtu", "y", NULL, offsetof(sink_config_t, max_mtu), 0),
    SD_BUS_PROPERTY("ChRangeMin", "y", NULL, offsetof(sink_config_t, ch_range_min), 0),
    SD_BUS_PROPERTY("ChRangeMax", "y", NULL, offsetof(sink_config_t, ch_range_max), 0),
    SD_BUS_PROPERTY("ACRangeMin", "q", NULL, offsetof(sink_config_t, ac_range_min), 0),
    SD_BUS_PROPERTY("ACRangeMax", "q", NULL, offsetof(sink_config_t, ac_range_max), 0),
    SD_BUS_PROPERTY("PDUBufferSize", "y", NULL, offsetof(sink_config_t, pdu_buffer_size), 0),
    SD_BUS_PROPERTY("AppConfigMaxSize", "q", NULL, offsetof(sink_config_t, app_config_max_size), 0),
    SD_BUS_PROPERTY("FirmwareVersion", "aq", get_firmware_version, 0, 0),

    /* Read parameters with node interrogation */
    SD_BUS_PROPERTY("CurrentAC", "q", current_ac_read_handler, 0, 0),
    SD_BUS_PROPERTY("CipherKeySet", "b", cipher_key_read_handler, 0, 0),
    SD_BUS_PROPERTY("AuthenticationKeySet", "b", authen_key_read_handler, 0, 0),
    SD_BUS_PROPERTY("StackStatus", "y", stack_status_read_handler, 0, 0),
    SD_BUS_PROPERTY("ACRangeMinCur", "q", cur_ac_range_handler, 0, 0),
    SD_BUS_PROPERTY("ACRangeMaxCur", "q", cur_ac_range_handler, 0, 0),

    /* Read/Write parameters with node interrogation */
    SD_BUS_WRITABLE_PROPERTY("NodeAddress", "u", node_add_read_handler, node_add_write_handler, 0, 0),
    SD_BUS_WRITABLE_PROPERTY("NodeRole", "y", node_role_read_handler, node_role_write_handler, 0, 0),
    SD_BUS_WRITABLE_PROPERTY("NetworkAddress", "u", network_add_read_handler, network_add_write_handler, 0, 0),
    SD_BUS_WRITABLE_PROPERTY("NetworkChannel", "y", network_channel_read_handler, network_channel_write_handler, 0, 0),
    SD_BUS_WRITABLE_PROPERTY("SinkCost", "y", sink_cost_read_handler, sink_cost_write_handler, 0, 0),
    SD_BUS_WRITABLE_PROPERTY("ChannelMap", "u", channel_map_read_handler_wrapper, channel_map_write_handler, 0, 0),

    /* Write only parameters (no write only concept so handled in read handler) */
    SD_BUS_WRITABLE_PROPERTY("CipherKey", "ay", read_key, set_cipher_key, 0, 0),
    SD_BUS_WRITABLE_PROPERTY("AuthenticationKey", "ay", read_key, set_authen_key, 0, 0),

    /* Methods related to config */
    SD_BUS_METHOD("SetStackState", "b", "b", set_stack_state, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("ClearCipherKey", "", "", clear_cipher_key, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("ClearAuthenticationKey", "", "", clear_authen_key, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("SetAppConfig", "yqay", "b", set_app_config, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetAppConfig", "", "yqay", get_app_config, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("SetACRange", "qq", "b", set_ac_range, SD_BUS_VTABLE_UNPRIVILEGED),

    /* Event generated when stack starts */
    SD_BUS_SIGNAL("StackStarted", "", 0),

    SD_BUS_VTABLE_END};

/* Typedef used to avoid warning at compile time */
typedef app_res_e (*func_1_param)(void * param);
typedef app_res_e (*func_2_param)(void * param1, void * param2);

/**
 * \brief   Generic function to read one or two parameters from node
 * \param   f
 *          The function to call to get the parameters (type func_1_t or  func_2_t)
 * \param   var1
 *          Pointer to first parameter
 * \param   var2
 *          Pointer to second parameter (can be NULL)
 * \param   var_name
 *          Parameter name
 * \return  True if correctly read, false otherwise
 */
static bool get_value_from_node(void * f, void * var1, void * var2, char * var_name)
{
    app_res_e res = APP_RES_INTERNAL_ERROR;
    if (var2 == NULL)
    {
        res = ((func_1_param) f)(var1);
    }
    else
    {
        res = ((func_2_param) f)(var1, var2);
    }

    if (res != APP_RES_OK)
    {
        LOGE("Cannot get %s from node\n", var_name);
        return false;
    }

    return true;
}

static bool initialize_unmodifiable_variables()
{
    bool res = true;

    res &= get_value_from_node(WPC_get_stack_profile, &m_sink_config.stack_profile, NULL, "Stack profile");
    res &= get_value_from_node(WPC_get_hw_magic, &m_sink_config.hw_magic, NULL, "Hw magic");
    res &= get_value_from_node(WPC_get_mtu, &m_sink_config.max_mtu, NULL, "MTU");
    res &= get_value_from_node(WPC_get_pdu_buffer_size, &m_sink_config.pdu_buffer_size, NULL, "PDU Buffer Size");
    res &= get_value_from_node(WPC_get_channel_limits,
                               &m_sink_config.ch_range_min,
                               &m_sink_config.ch_range_max,
                               "Channel Range");
    res &= get_value_from_node(WPC_get_access_cycle_limits,
                               &m_sink_config.ac_range_min,
                               &m_sink_config.ac_range_max,
                               "AC Range");
    res &= get_value_from_node(WPC_get_app_config_data_size,
                               &m_sink_config.app_config_max_size,
                               NULL,
                               "App Config Max size");

    if (WPC_get_firmware_version(m_sink_config.version) == APP_RES_OK)
    {
        LOGI("Stack version is: %d.%d.%d.%d\n",
             m_sink_config.version[0],
             m_sink_config.version[1],
             m_sink_config.version[2],
             m_sink_config.version[3]);
    }
    else
    {
        res = false;
    }

    if (!res)
    {
        LOGE("All the static settings cannot be read\n");
    }

    return res;
}

static void on_stack_boot_status(uint8_t status)
{
    /* After a reboot, read again the variable as it can be because
     * of an otap and variables may change
     */
    initialize_unmodifiable_variables();

    if (status == 0)
    {
        LOGD("Stack restarted\n");
        send_dbus_signal("StackStarted");
    }
}

int Config_Init(sd_bus * bus, char * object, char * interface)
{
    int r;
    uint8_t status;

    m_bus = bus;
    m_object = object;
    m_interface = interface;

    /* Register for stack status */
    if (WPC_register_for_stack_status(on_stack_boot_status) != APP_RES_OK)
    {
        LOGE("Fail to register for stack state\n");
        return -1;
    }

    /* Read unmodifiable config from sink */
    initialize_unmodifiable_variables();

    /* Install the config vtable */
    r = sd_bus_add_object_vtable(bus, &m_slot, object, interface, config_vtable, &m_sink_config);

    if (r < 0)
    {
        LOGE("Fail to issue method call: %s\n", strerror(-r));
        return r;
    }

    /* Get the current stack status for informative purpose */
    if (WPC_get_stack_status(&status) == APP_RES_OK)
    {
        LOGI("Stack is %s\n", status == 0 ? "started" : "stopped");
    }
    else
    {
        LOGE("Cannot determine stack state\n");
    }

    return 0;
}

void Config_Close()
{
    if (m_slot != NULL)
    {
        sd_bus_slot_unref(m_slot);
    }
}
