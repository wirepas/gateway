# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import logging
import os
import sys
from datetime import datetime

from wirepas_gateway.dbus.dbus_client import BusClient


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
        logging.info(
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
            logging.info("Sink connected with config: %s", sink.read_config())


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

    debug_level = "{0}".format(debug_level.upper())

    # Create a "Print Client" object and enable his logger
    obj = PrintClient()
    logging.basicConfig(
        format='%(asctime)s | [%(levelname)s] %(name)s@%(filename)s:%(lineno)d:%(message)s',
        level=debug_level,
        stream=sys.stdout
    )
    obj.run()


if __name__ == "__main__":

    main()
