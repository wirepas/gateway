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

int main(int argc, char * argv[])
{
    unsigned long bitrate = 125000;
    char full_service_name[MAX_SIZE_SERVICE_NAME];
    int r;
    int c;
    unsigned int sink_id = 0;
    uint16_t mesh_version;
    unsigned int max_poll_fail_duration = UNDEFINED_MAX_POLL_FAIL_DURATION;

    /* Parse arguments */
    while ((c = getopt(argc, argv, "b:p:i:d:")) != -1)
    {
        switch (c)
        {
            case 'b':
                /* Get the bitrate */
                bitrate = strtoul(optarg, NULL, 0);
                LOGI("Bitrate set to %d\n", bitrate);
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
                LOGE("Parameters are: -b <bitrate> -p <port> -i <sink_id>\n");
                return EXIT_FAILURE;
        }
    }

    /* Generate full service name */
    if (!get_service_name(full_service_name, sink_id))
    {
        return EXIT_FAILURE;
    }

    LOGI("Starting Sink service:\n\t-Port is %s\n\t-Bitrate is %d\n\t-Dbus "
         "Service name is %s\n",
         port_name,
         bitrate,
         full_service_name);

    if (WPC_initialize(port_name, bitrate) != APP_RES_OK)
    {
        LOGE("Cannot open serial sink connection (%s)\n", port_name);
        return EXIT_FAILURE;
    }

    if (max_poll_fail_duration != UNDEFINED_MAX_POLL_FAIL_DURATION) {
        if (WPC_set_max_poll_fail_duration(max_poll_fail_duration))
        {
            LOGE("Cannot set max poll fail duration (%d)\n", max_poll_fail_duration);
            return EXIT_FAILURE;
        }
    }

    /* Do sanity check to test connectivity with sink */
    if (WPC_get_mesh_API_version(&mesh_version) != APP_RES_OK)
    {
        LOGE("Cannot establish communication with sink over UART\n");
        return EXIT_FAILURE;
    }
    LOGI("Node is running mesh API version %d\n", mesh_version);

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
