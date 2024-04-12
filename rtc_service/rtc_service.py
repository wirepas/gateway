# Copyright 2023 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import argparse
import datetime
import logging
import ntplib
import os
import socket
import struct
import sys
from time import sleep, time
from threading import Thread

from wirepas_gateway.dbus.dbus_client import BusClient
import wirepas_mesh_messaging as wmm


PKG_NAME = "rtc_service"
RTC_VERSION = 1

BROADCAST_ADDRESS = 0xFFFFFFFF

RTC_SOURCE_EP = 78
RTC_DEST_EP = 79

RTC_ID_TIMESTAMP = 0
RTC_ID_TIMEZONE_OFFSET = 1


def encode_tlv_item(elt_type, length, value, packing):
    """
    Encode a new TLV item.

    Args:
        elt_type (int): Type of the element to encode.
        length (int): Number of bytes of the value to be encoded.
        value: Value to encode. Note: Value should have a specific type
               corresponding to the packing parameter.
        packing (str): String representing the format characters allowing
                       the conversion between C and Python bytes when packing the value.
                       See https://docs.python.org/3/library/struct.html#format-characters.
    """
    assert (0 <= elt_type <= 0xFF), "A TLV type must be include between 0 and 255"
    assert isinstance(length, int), "A TLV length must be an integer"
    return bytes(struct.pack("<bb" + packing, elt_type, length, value))


def encode_tlv(timestamp_ms, timezone_offset_s=0):
    """
    Encode a RTC message with TLV.
    Each of the RTC item are encoding as:
    Type of the item - Length of the value to encode - value to encode.

    Args:
        timestamp_ms: Current global time of the network in ms.
        timezone_offset_s: Offset of the timezone in seconds. (default: 0)
    """
    buffer = b""
    if timestamp_ms is not None:
        buffer += encode_tlv_item(RTC_ID_TIMESTAMP, 8, timestamp_ms, "Q")
    if timezone_offset_s is not None:
        buffer += encode_tlv_item(RTC_ID_TIMEZONE_OFFSET, 4, timezone_offset_s, "l")
    return buffer


class SynchronizationThread(Thread):

    def __init__(
        self,
        period,
        retry_period,
        timezone_offset_s,
        timezone_from_gateway_clock,
        get_time_from_local,
        ntp_server_address,
        sink_manager
    ):
        """
            Thread sending periodically time to synchronize the network.

        Args:
            period: The period to send gateway time to the network
            retry_period: Period in seconds of the retries sending
                the ntp rtc time when it couldn't be sent to the network.
            timezone_offset_s: Offset of the local time in seconds
                if timezone_from_gateway_clock is False.
            timezone_from_gateway_clock: True if timezone offset must be taken from gateway clock.
                False (default) means that the timezone offset is given by timezone_offset_s argument.
            get_time_from_local: False(default) will force the gateway to ask time
                from a ntp server before sending it to the network
                True means that the time is taken directly from gateway.
                Note: You must assure that gateway are synchronized if set to True
            ntp_server_address: Address of the ntp server to query the time
                                if it is taken from an ntp server.
            sink_manager: The sink manager to send sink the rtc informations
        """
        Thread.__init__(self)

        # Daemonize thread to exit with full process
        self.daemon = True

        # How often to send time
        self.period = period
        self.retry_period = retry_period
        self.timezone_from_gateway_clock = timezone_from_gateway_clock
        if timezone_from_gateway_clock is True:
            self.timezone_offset_s = datetime.datetime.now(datetime.timezone.utc).astimezone().utcoffset().seconds
            logging.info("Timezone offset is initialized with gateway clock")
        else:
            self.timezone_offset_s = timezone_offset_s
            logging.info("Timezone offset is initialized with parameter")
        logging.info(f"Timezone offset is set to {self.timezone_offset_s}s")

        self.get_time_from_local = get_time_from_local
        self.ntp_server_address = ntp_server_address
        if not self.get_time_from_local:
            logging.info("RTC time is taken from a ntp server")
            self.ntp_client = ntplib.NTPClient()
        else:
            logging.info("RTC time is taken from local time")
        self.sink_manager = sink_manager
        logging.info(f"Expected RTC sending period is set to {self.period}s")

    def publish_time(self) -> bool:
        """
        Publish the rtc time in the network.
        Return True if the time could published, return False otherwise.
        """
        if not self.get_time_from_local:
            try:
                req = self.ntp_client.request(self.ntp_server_address, version=3)
                timestamp = req.dest_time + req.offset
            except (ntplib.NTPException, socket.gaierror) as err:
                logging.warning("An error occured when trying to get time from NTP server. (%s)", err)
                return False
        else:
            timestamp = time()

        timestamp_ms = int(timestamp*1000)
        data_payload = RTC_VERSION.to_bytes(2, "little") + encode_tlv(timestamp_ms, self.timezone_offset_s)

        sinks = self.sink_manager.get_sinks()
        if not sinks:
            logging.error("No sinks are detected!")
            return False

        logging.info("Send rtc message to the network")
        logging.debug("Payload: %s", data_payload.hex())
        sent_to_one_sink: bool = False

        for sink in sinks:
            start = time()
            res = sink.send_data(
                dst=BROADCAST_ADDRESS,
                src_ep=RTC_SOURCE_EP,
                dst_ep=RTC_DEST_EP,
                qos=0,
                initial_time=0,
                data=data_payload
            )
            logging.debug("time elapsed to send RTC time through the gateway: %dms",
                          int((time() - start) * 1000))
            if res == wmm.GatewayResultCode.GW_RES_OK:
                sent_to_one_sink = True
            else:
                logging.error("rtc time couldn't be sent to %s sink: %s", sink.sink_id, res)

        return sent_to_one_sink

    def run(self):
        """
        Main loop that send periodically gateway time to the network.
        """
        while True:
            if self.publish_time():
                sleep(self.period)
            else:
                sleep(self.retry_period)


class RtcService(BusClient):
    """
    Implementation of the RTC service

    Send periodically RTC time to the network.
    """
    def __init__(self, settings, **kwargs):

        super(RtcService, self).__init__(**kwargs)
        self.synchronization_thread = SynchronizationThread(
            settings.rtc_synchronization_period_s,
            settings.rtc_retry_period_s,
            settings.timezone_offset_s,
            settings.timezone_from_gateway_clock,
            settings.get_time_from_local,
            settings.ntp_server_address,
            self.sink_manager,
        )
        self.synchronization_thread.start()


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
        default=os.environ.get("WM_RTC_SYNCHRONIZATION_PERIOD_S", 1200),
        action="store",
        type=str2int,
        help=("Period of time to send a new rtc time in the network."),
    )

    parser.add_argument(
        "--rtc_retry_period_s",
        default=os.environ.get("WM_RTC_RETRY_PERIOD_S", 1),
        action="store",
        type=str2int,
        help=("Period in seconds of the retries sending the rtc time when it couldn't be sent to the network."
              "Note: It might take additional 5 seconds to know that the rtc time can't be retrieved.")
    )

    parser.add_argument(
        "--timezone_from_gateway_clock",
        default=os.environ.get("WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK", False),
        action="store",
        type=str2bool,
        help=("True if timezone offset must be taken from gateway clock."
              "False (default) means that the timezone offset is"
              "given by timezone_offset_s argument"),
    )

    parser.add_argument(
        "--timezone_offset_s",
        default=os.environ.get("WM_RTC_TIMEZONE_OFFSET_S", 0),
        action="store",
        type=str2int,
        help=("Timezone offset of the local time if WM_RTC_TIMEZONE_FROM_GATEWAY_CLOCK is False."),
    )

    parser.add_argument(
        "--get_time_from_local",
        default=os.environ.get("WM_RTC_GET_TIME_FROM_LOCAL", False),
        action="store",
        type=str2bool,
        help=("False(default) will force the gateway to ask time from a ntp server"
              "before sending it to the network"
              "True means that the time is taken directly from gateway."
              "Note: You must assure that gateway are synchronized if set to True"),
    )

    parser.add_argument(
        "--ntp_server_address",
        default=os.environ.get("WM_RTC_NTP_SERVER_ADDRESS", "pool.ntp.org"),
        action="store",
        type=str,
        help=("Address of the ntp server to query the time if it is taken from an ntp server. "
              "(WM_RTC_GET_TIME_FROM_LOCAL must be set to False "
              "for that option to be taken into account)")
    )

    settings = parser.parse_args()

    # Set default debug level
    debug_level = "info"

    try:
        debug_level = os.environ["WM_DEBUG_LEVEL"]
    except KeyError:
        pass

    debug_level = "{0}".format(debug_level.upper())

    # enable its logger
    logging.basicConfig(
        format=f'%(asctime)s | [%(levelname)s] {PKG_NAME}@%(filename)s:%(lineno)d:%(message)s',
        level=debug_level,
        stream=sys.stdout
    )

    RtcService(settings=settings).run()


if __name__ == "__main__":
    main()
