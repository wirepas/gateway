# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import os
import logging
from datetime import datetime

from wirepas_gateway.dbus.dbus_client import BusClient
from wirepas_gateway.utils import setup_log


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
            "[{}] Sink {} FROM {} TO {} on EP {} Data Size is {}".format(
                datetime.utcfromtimestamp(int(timestamp / 1000)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                sink_id,
                src,
                dst,
                dst_ep,
                len(data),
            )
        )

    def on_sink_connected(self, name):
        sink = self.sink_manager.get_sink(name)

        if sink is not None:
            # Read Stack status of sink on connection
            self.logger.info(
                "Sink connected with config: {}".format(sink.read_config())
            )


def main(log_name="print_client"):

    try:
        debug_level = os.environ["DEBUG_LEVEL"]
    except KeyError:
        debug_level = "info"

    logger = setup_log(log_name, level=debug_level)
    obj = PrintClient()
    obj.logger = logger
    obj.run()


if __name__ == "__main__":

    main()
