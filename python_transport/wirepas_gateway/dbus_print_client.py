# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import os
from datetime import datetime

from wirepas_gateway.dbus.dbus_client import BusClient
from wirepas_gateway.utils import LoggerHelper


class PrintClient(BusClient):
    """
    Simple class example that print all received message from dbus
    """

    def on_data_received(
        self,
        sink_id,
        timestamp,
        src,
        dst,
        src_ep,
        dst_ep,
        travel_time,
        qos,
        hop_count,
        data,
    ):
        """ logs incoming data from the WM network """
        self.logger.info(
            "[%s] Sink %s FROM %d TO %d on EP %d Data Size is %d",
            datetime.utcfromtimestamp(int(timestamp / 1000)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            sink_id,
            src,
            dst,
            dst_ep,
            len(data),
        )

    def on_sink_connected(self, name):
        sink = self.sink_manager.get_sink(name)

        if sink is not None:
            # Read Stack status of sink on connection
            self.logger.info("Sink connected with config: %s", sink.read_config())


def main():

    # Set default debug level
    debug_level = "info"
    try:
        debug_level = os.environ["DEBUG_LEVEL"]
        print(
            "Deprecated environment variable DEBUG_LEVEL "
            "(it will be dropped from version 2.x onwards)"
            " please use WM_DEBUG_LEVEL instead."
        )
    except KeyError:
        pass

    try:
        debug_level = os.environ["WM_DEBUG_LEVEL"]
    except KeyError:
        pass

    log = LoggerHelper(module_name=__name__, level=debug_level)
    logger = log.setup()

    obj = PrintClient()
    obj.logger = logger
    obj.run()


if __name__ == "__main__":

    main()
