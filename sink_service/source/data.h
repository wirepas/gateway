/* Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
 *
 * See file LICENSE for full license details.
 *
 */

#ifndef SINK_MANAGER_SOURCE_DATA_H_
#define SINK_MANAGER_SOURCE_DATA_H_

#include <systemd/sd-bus.h>

/**
 * \brief   Initialize the data module
 * \param   bus
 *          The sd_bus instance to publish the config interface
 *\param    object
 *\param    interface
 *\param    downlink_limit
            If > 0, max number of downlink messages being queued in parallel
 * \return  0 if initialization succeed, an error code otherwise
 * \note    Connection with sink must be ready before calling this module
 */
int Data_Init(sd_bus * bus, char * object, char * interface, size_t downlink_limit);

void Data_Close();

#endif /* SINK_MANAGER_SOURCE_DATA_H_ */
