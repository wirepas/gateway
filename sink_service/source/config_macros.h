/* Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
 *
 * See file LICENSE for full license details.
 *
 */

/*
 * \file    config_macros.h
 *
 * \brief   This file contains several macros to ease dbus property
 *          handler declaration
 */

#ifndef _CONFIG_MACROS_H_
#define _CONFIG_MACROS_H_

/** static buffer used to generate dbus error message (one for each module) */
static char error_message[100];

/** Helper to generate error message (TODO: add conversion from app-res-e to string) */
#define SET_WPC_ERROR(__bus_error_p__, __function_name__, __wpc_res__)                         \
    snprintf(error_message, 100, "[%s]: C Mesh Lib ret = %d", __function_name__, __wpc_res__); \
    sd_bus_error_set_const(__bus_error_p__, "com.wirepas.sink.config.error", error_message);

/** Helper macro to generate a generic read handler */
#define HANDLER_READ(name, func, c_type, dbus_type)        \
    static int name##_read_handler(sd_bus * bus,           \
                                   const char * path,      \
                                   const char * interface, \
                                   const char * property,  \
                                   sd_bus_message * reply, \
                                   void * userdata,        \
                                   sd_bus_error * error)   \
    {                                                      \
        c_type var;                                        \
        app_res_e res = APP_RES_INTERNAL_ERROR;            \
        res = func(&var);                                  \
                                                           \
        if (res != APP_RES_OK)                             \
        {                                                  \
            SET_WPC_ERROR(error, #func, res);              \
            LOGE("Cannot get %s (ret=%d)\n", #name, res);  \
            return -EINVAL;                                \
        }                                                  \
        else                                               \
        {                                                  \
            sd_bus_message_append(reply, dbus_type, var);  \
            return 0;                                      \
        }                                                  \
    }

/** Helper macro to generate a generic write handler */
#define HANDLER_WRITE(name, func, c_type, dbus_type)                \
    static int name##_write_handler(sd_bus * bus,                   \
                                    const char * path,              \
                                    const char * interface,         \
                                    const char * property,          \
                                    sd_bus_message * value,         \
                                    void * userdata,                \
                                    sd_bus_error * error)           \
    {                                                               \
        int r;                                                      \
        c_type var;                                                 \
        app_res_e res = APP_RES_INTERNAL_ERROR;                     \
                                                                    \
        r = sd_bus_message_read(value, dbus_type, &var);            \
        if (r < 0)                                                  \
        {                                                           \
            LOGE("Cannot get param %s: %s\n", #name, strerror(-r)); \
            sd_bus_error_set_errno(error, r);                       \
            return r;                                               \
        }                                                           \
        res = func(var);                                            \
        if (res != APP_RES_OK)                                      \
        {                                                           \
            SET_WPC_ERROR(error, #func, res);                       \
            LOGE("Cannot set %s (ret=%d)\n", #name, res);           \
            return -EINVAL;                                         \
        }                                                           \
        LOGD("Value %d written for %s\n", var, #name);              \
        return 0;                                                   \
    }

/*
 * Helper macros to generate a property read handler for a given type
 */
#define HANDLER_READ_BOOL(name, func) HANDLER_READ(name, func, bool, "b")
#define HANDLER_READ_UINT8(name, func) HANDLER_READ(name, func, uint8_t, "y")
#define HANDLER_READ_UINT16(name, func) HANDLER_READ(name, func, uint16_t, "q")
#define HANDLER_READ_UINT32(name, func) HANDLER_READ(name, func, uint32_t, "u")

/*
 * Helper macros to generate a property write handler for a given type
 */
#define HANDLER_WRITE_UINT8(name, func) HANDLER_WRITE(name, func, uint8_t, "y")
#define HANDLER_WRITE_UINT16(name, func) \
    HANDLER_WRITE(name, func, uint16_t, "q")
#define HANDLER_WRITE_UINT32(name, func) \
    HANDLER_WRITE(name, func, uint32_t, "u")

#endif /* _CONFIG_MACROS_H_ */
