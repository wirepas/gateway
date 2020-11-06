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
#include <unistd.h>
#include <libgen.h>

#include <systemd/sd-bus.h>

#include "wpc.h"
#include "config.h"
#include "data.h"
#include "otap.h"

#define LOG_MODULE_NAME "Main"
#define MAX_LOG_LEVEL INFO_LOG_LEVEL
#include "logger.h"

/* Default serial port */
static char * port_name = "/dev/ttyACM0";

/* Maximum size of dbus service name */
#define MAX_SIZE_SERVICE_NAME 100
/* Prefix for sink service name */
#define BASE_SERVICE_NAME "com.wirepas.sink.sink0"
/* max poll fail duration undefined */
#define UNDEFINED_MAX_POLL_FAIL_DURATION 0xffffffff

/* Dbus bus instance*/
static sd_bus * m_bus = NULL;

/**
 * \brief   Generate a unique service name based on port name
 * \param   service_name
 *          Unique service name generated
 * \param   sink_id
 *          sink id used for this sink between 0 and 9
 * \return  True if successful, false otherwise
 */
static bool get_service_name(char service_name[MAX_SIZE_SERVICE_NAME], unsigned int sink_id)
{
    // Change last character of service name
    if (sink_id > 9)
    {
        LOGE("Sink id is not in [0..9]\n");
        return false;
    }

    // First copy base service name
    memcpy(service_name, BASE_SERVICE_NAME, sizeof(BASE_SERVICE_NAME));

    // Modify last char
    service_name[sizeof(BASE_SERVICE_NAME) - 2] = sink_id + 0x30;
    return true;
}

/**
 * \brief   Obtains environment parameters to control sink settings
 * \param   baudrate
 *          Pointer where to store baudrate value (if any)
 * \param   port_name
 *          Pointer where to store port_name value (if any)
 * \param   sink_id
 *          Pointer where to store sink_id value (if any)
 * \param   max_poll_fail_duration
 *          Pointer where to store max_poll_fail_duration value (if any)
 */
static void get_env_parameters(unsigned long * baudrate,
                               char ** port_name,
                               unsigned int * sink_id,
                               unsigned int * max_poll_fail_duration)
{
    char * ptr;

    // Read WM_GW_SINK_BAUDRATE and WM_GW_SINK_BITRATE
    if (((ptr = getenv("WM_GW_SINK_BAUDRATE")) != NULL) ||
        ((ptr = getenv("WM_GW_SINK_BITRATE")) != NULL))
    {
        *baudrate = strtoul(ptr, NULL, 0);
        LOGI("WM_GW_SINK_BAUDRATE: %lu\n", *baudrate);
    }
    if ((ptr = getenv("WM_GW_SINK_ID")) != NULL)
    {
        *sink_id = strtoul(ptr, NULL, 0);
        LOGI("WM_GW_SINK_ID: %lu\n", *sink_id);
    }
    if ((ptr = getenv("WM_GW_SINK_UART_PORT")) != NULL)
    {
        *port_name = ptr;
        LOGI("WM_GW_SINK_UART_PORT: %s\n", *port_name);
    }
    if ((ptr = getenv("WM_GW_SINK_MAX_POLL_FAIL_DURATION")) != NULL)
    {
        *max_poll_fail_duration = strtoul(ptr, NULL, 0);
        LOGI("WM_GW_SINK_MAX_POLL_FAIL_DURATION: %lu\n", *max_poll_fail_duration);
    }
}

// Usual baudrate to test in automatic mode
// They are the ones frequently used in dual mcu application
// 125000 is first as it was the original default value
static const unsigned long auto_baudrate_list[] = {125000, 115200, 1000000};

static int open_and_check_connection(unsigned long baudrate, char * port_name)
{
    uint16_t mesh_version;
    if (WPC_initialize(port_name, baudrate) != APP_RES_OK)
    {
        LOGE("Cannot open serial sink connection (%s)\n", port_name);
        return EXIT_FAILURE;
    }

    /* Check the connectivity with sink by reading mesh version */
    if (WPC_get_mesh_API_version(&mesh_version) != APP_RES_OK)
    {
        LOGD("Cannot establish communication with sink with baudrate %d bps\n", baudrate);
        WPC_close();
        return EXIT_FAILURE;
    }

    LOGI("Node is running mesh API version %d (uart baudrate is %d bps)\n", mesh_version, baudrate);
    return 0;
}

int main(int argc, char * argv[])
{
    unsigned long baudrate = 0;
    char full_service_name[MAX_SIZE_SERVICE_NAME];
    int r;
    int c;
    unsigned int sink_id = 0;
    unsigned int max_poll_fail_duration = UNDEFINED_MAX_POLL_FAIL_DURATION;

    /* Acquires environment parameters */
    get_env_parameters(&baudrate, &port_name, &sink_id, &max_poll_fail_duration);

    /* Parse command line arguments - take precedence over environmental ones */
    while ((c = getopt(argc, argv, "b:p:i:d:")) != -1)
    {
        switch (c)
        {
            case 'b':
                /* Get the baudrate */
                baudrate = strtoul(optarg, NULL, 0);
                LOGI("Baudrate set to %d\n", baudrate);
                break;
            case 'p':
                /* Get the port name */
                port_name = optarg;
                break;
            case 'i':
                /* Get the sink id to generate service name */
                sink_id = strtoul(optarg, NULL, 0);
                break;
            case 'd':
                max_poll_fail_duration = strtoul(optarg, NULL, 0);
                break;
            case '?':
            default:
                LOGE("Error in argument parsing\n");
                LOGE("Parameters are: -b <baudrate> -p <port> -i <sink_id>\n");
                return EXIT_FAILURE;
        }
    }

    /* Generate full service name */
    if (!get_service_name(full_service_name, sink_id))
    {
        return EXIT_FAILURE;
    }

    LOGI("Starting Sink service:\n\t-Port is %s\n\t-Baudrate is %d\n\t-Dbus "
         "Service name is %s\n",
         port_name,
         baudrate,
         full_service_name);

    if (baudrate != 0)
    {
        // The baudrate to use is given
        if (open_and_check_connection(baudrate, port_name) != 0)
        {
            LOGE("Cannot establish communication with sink\n");
            return EXIT_FAILURE;
        }
    }
    else
    {
        // Automatic baudrate, test the list one by one
        size_t number_of_baudrates =
            sizeof(auto_baudrate_list) / sizeof(auto_baudrate_list[0]);
        size_t i;
        for (i = 0; i < number_of_baudrates; i++)
        {
            LOGI("Auto baudrate: testing %d bps\n", auto_baudrate_list[i]);
            if (open_and_check_connection(auto_baudrate_list[i], port_name) != 0)
            {
                LOGD("Cannot establish communication with sink\n");
            }
            else
            {
                LOGI("Uart baudrate found: %d bps\n", auto_baudrate_list[i]);
                break;
            }
        }

        if (i == number_of_baudrates)
        {
            LOGE("Cannot establish communication with sink with different "
                 "tested baudrate\n");
            return EXIT_FAILURE;
        }
    }

    if (max_poll_fail_duration != UNDEFINED_MAX_POLL_FAIL_DURATION)
    {
        if (WPC_set_max_poll_fail_duration(max_poll_fail_duration))
        {
            LOGE("Cannot set max poll fail duration (%d)\n", max_poll_fail_duration);
            return EXIT_FAILURE;
        }
    }

    /* Connect to the user bus */
    r = sd_bus_open_system(&m_bus);
    if (r < 0)
    {
        LOGE("Failed to connect to user bus: %s\n", strerror(-r));
        goto finish;
    }

    if (Config_Init(m_bus, "/com/wirepas/sink", "com.wirepas.sink.config1") < 0)
    {
        LOGE("Cannot initialize config module\n");
        r = -1;
        goto finish;
    }

    if (Data_Init(m_bus, "/com/wirepas/sink", "com.wirepas.sink.data1") < 0)
    {
        LOGE("Cannot initialize data module\n");
        r = -1;
        goto finish;
    }

    if (Otap_Init(m_bus, "/com/wirepas/sink", "com.wirepas.sink.otap1") < 0)
    {
        LOGE("Cannot initialize otap module\n");
        r = -1;
        goto finish;
    }

    /* Use the service name based on port name */
    r = sd_bus_request_name(m_bus, full_service_name, 0);
    if (r < 0)
    {
        LOGE("Failed to acquire service name %s: %s\n", full_service_name, strerror(-r));
        goto finish;
    }

    for (;;)
    {
        /* Process requests */
        r = sd_bus_process(m_bus, NULL);
        if (r < 0)
        {
            LOGE("Failed to process bus: %s\n", strerror(-r));
            goto finish;
        }

        /* we processed a request, try to process another one, right-away */
        if (r > 0)
            continue;

        /* Wait for the next request to process */
        r = sd_bus_wait(m_bus, (uint64_t) -1);
        if (r < 0)
        {
            LOGE("Failed to wait on bus: %s\n", strerror(-r));
            goto finish;
        }
    }

finish:
    Otap_Close();
    Data_Close();
    Config_Close();
    sd_bus_unref(m_bus);
    WPC_close();

    return r < 0 ? EXIT_FAILURE : EXIT_SUCCESS;
}
