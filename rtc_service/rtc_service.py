# Copyright 2022 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import argparse
import datetime
import logging
import ntplib
import os
import struct
import sys
from time import sleep, time
from threading import Thread

from wirepas_gateway.dbus.dbus_client import BusClient


BROADCAST_ADDRESS = 0xFFFFFFFF  # Broadcast
INITIAL_DELAY_MS = 0

# TODO, determine true Endpoints
RTC_SOURCE_EP = 78
RTC_DEST_EP = 78


class SynchronizationThread(Thread):

    def __init__(
        self,
        period,
        timezone_offset_s,
        timezone_from_gateway_clock,
        sink_manager
    ):
        """
            Thread sending periodically time to synchronize the mesh network.
        Args:
            period: the period to send gateway time to the mesh network
            sink_manager: the sink manager to send sink the rtc informations
        """
        Thread.__init__(self)

        # Daemonize thread to exit with full process
        self.daemon = True

        # How often to send time
        self.period = period
        self.timezone_from_gateway_clock = timezone_from_gateway_clock
        if timezone_from_gateway_clock is True:
            self.timezone_offset_s = datetime.datetime.now(datetime.timezone.utc).astimezone().utcoffset().seconds
        else:
            self.timezone_offset_s = timezone_offset_s

        self.ntp_client = ntplib.NTPClient()
        self.sink_manager = sink_manager
        logging.info(f"Expected RTC sending period is set to {self.period}s")

        self.running = False

    def publish_time(self):
        """
        Publish the gateway time in the network.
        """
        req = self.ntp_client.request('europe.pool.ntp.org', version=3)
        timer = req.dest_time+req.offset
        # timer = time()
        timer_ms = int(timer*1000)
        data_payload = bytes(struct.pack("<Ql",
                    timer_ms, self.timezone_offset_s))
        # TODO: cbor encoding to be backward compatible

        logging.info(f"Send rtc={timer_ms} to the network")
        for sink in self.sink_manager.get_sinks():
            start = time()
            sink.send_data(
                dst=BROADCAST_ADDRESS,
                src_ep=RTC_SOURCE_EP,
                dst_ep=RTC_DEST_EP,
                qos=0,
                initial_time=INITIAL_DELAY_MS,
                data=data_payload,
                is_unack_csma_ca=False,
                hop_limit=0,
            )
            logging.info(f"time elapsed to send ntp through the gateway: {int((time()-start)*1000)}ms")

    def run(self):
        """
        Main loop that send periodically gateway time to the network.
        """
        self.running = True

        while self.running:
            self.publish_time()
            sleep(self.period)

    def stop(self):
        """
        Stop the periodical sending gateway status thread.
        """
        self.running = False

class RtcService(BusClient):
    """
    Implementation of gateway to backend protocol

    Get all the events from DBUS and publih it with right format
    for gateways
    """
    def __init__(self, settings, **kwargs):

        super(RtcService, self).__init__(**kwargs)

        self.ntp_client = ntplib.NTPClient()
        self.synchronization_thread = SynchronizationThread(
            settings.rtc_synchronization_period_s,
            settings.timezone_offset_s,
            settings.timezone_from_gateway_clock,
            self.sink_manager,
        )
        self.synchronization_thread.start()


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
        if (src_ep == RTC_SOURCE_EP and dst_ep == RTC_DEST_EP):
            req = self.ntp_client.request('europe.pool.ntp.org', version=3)
            timer = req.orig_time+req.offset
            logging.info(f"Difference between rtc and expected sink time to be {int((timer)*1000) - (int.from_bytes(data, 'little')+travel_time)}ms from node {src}")
            return  # rtc is not treated in the backend

    def on_stack_started(self, name):
        logging.debug("Sink started: %s", name)

    def on_stack_stopped(self, name):
        logging.debug("Sink stopped: %s", name)

    def on_sink_connected(self, name):
        logging.info("Sink connected, sending new configs")

    def on_sink_disconnected(self, name):
        logging.info("Sink disconnected, sending new configs")


def str2bool(value):
    """ Ensures string to bool conversion """
    if isinstance(value, bool):
        return value
    if value.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif value.lower() in ("no", "false", "f", "n", "0", ""):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def str2int(value):
    """ Ensures string to bool conversion """
    try:
        value = int(value)
    except ValueError:
        if value == "":
            value = 0
        else:
            raise argparse.ArgumentTypeError("Integer value expected.")
    return value


def main():
    """
        Main service for rtc service module
    """
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

    parser.add_argument(
        "--rtc_synchronization_period_s",
        default=os.environ.get("WM_RTC_SYNCHRONIZATION_PERIOD_S", 20*60),
        action="store",
        type=str2int,
        help=("Period of time before sending a new rtc time in the network."),
    )

    parser.add_argument(
        "--timezone_from_gateway_clock",
        default=os.environ.get("WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK", False),
        action="store",
        type=str2bool,
        help=("True if timezone offset must be taken from gateway clock."
              "False (default) means that the timezone offset is"
              "given by utc_to_local_offset_s argument"),
    )

    parser.add_argument(
        "--timezone_offset_s",
        default=os.environ.get("WM_RTC_TIMEZONE_OFFSET_S", 0),
        action="store",
        type=str2int,
        help=("Timezone offset of the local time if WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK is False."),
    )

    settings = parser.parse_args()

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

    # enable its logger
    logging.basicConfig(
        format='%(asctime)s | [%(levelname)s] %(name)s@%(filename)s:%(lineno)d:%(message)s',
        level=debug_level,
        stream=sys.stdout
    )

    RtcService(settings=settings).run()


if __name__ == "__main__":
    main()
