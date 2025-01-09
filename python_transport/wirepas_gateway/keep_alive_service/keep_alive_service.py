# Copyright 2024 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
from enum import IntEnum
import logging
import struct
from time import time, sleep
from threading import Thread

import wirepas_mesh_messaging as wmm


KEEP_ALIVE_SERVICE_VERSION = 0x01
KEEP_ALIVE_SRC_EP = 67
KEEP_ALIVE_DST_EP = 67

# Timeouts and periods used for the keep alive service.
WM_MSG_RETRY_PERIOD_S = 1
KEEP_ALIVE_MSG_RECONNECTION_PERIOD_S = 60

BROADCAST_ADDRESS = 0xFFFFFFFF


class KeepAliveType(IntEnum):
    """ Keep alive fields TLV type enumerate. """
    VERSION_TYPE = 0x01
    GATEWAY_STATUS_TYPE = 0x02
    RTC_TIMESTAMP_TYPE = 0x03
    TIME_ZONE_OFFSET_TYPE = 0x04
    KEEP_ALIVE_INTERVAL_TYPE = 0x05


class KeepAliveMessage():
    """
    Class to store keep alive message attributes.

    Attributes:
        version: The version number for the keep-alive message.
        gateway_status: The running status of the gateway.
            Bit 0: Backhaul (MQTT broker) Connectivity (0 = Disconnected, 1 = Connected)
            Bits 1-7: Reserved for future use or other status indicators
        rtc_timestamp_ms: Unix epoch timestamp in ms (milliseconds since January 1, 1970).
        timezone_offset_mn: Time zone offset from UTC in minutes (-840 to +720).
        keep_alive_interval_s: Interval in seconds until the next keepalive message is expected.
    """
    def __init__(self, version, gateway_status=None, rtc_timestamp_ms=None,
                 timezone_offset_mn=None, keep_alive_interval_s=None):
        self.version = version
        self.gateway_status = gateway_status
        self.rtc_timestamp_ms = rtc_timestamp_ms
        self.timezone_offset_mn = timezone_offset_mn
        self.keep_alive_interval_s = keep_alive_interval_s

    @classmethod
    def encode_tlv_item(cls, elt_type, length, value, packing):
        """
        Encode a new TLV item in little endian.

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

    def encode_tlv(self):
        """
        Encode a keep alive message with TLV.
        Each of the RTC item are encoding as:
        Type of the item - Length of the value to encode - value to encode.
        """
        logging.debug(f"Prepare keep alive message with version={self.version}, "
                      f"gateway_status={self.gateway_status}, "
                      f"rtc_timestamp_ms={self.rtc_timestamp_ms}, "
                      f"timezone_offset_mn={self.timezone_offset_mn} and "
                      f"keep_alive_interval_s={self.keep_alive_interval_s}")

        buffer = bytes()
        buffer += KeepAliveMessage.encode_tlv_item(
            KeepAliveType.VERSION_TYPE, 1, KEEP_ALIVE_SERVICE_VERSION, "B"
        )
        if self.gateway_status is not None:
            buffer += KeepAliveMessage.encode_tlv_item(
                KeepAliveType.GATEWAY_STATUS_TYPE, 1, self.gateway_status, "B"
            )
        if self.rtc_timestamp_ms is not None:
            buffer += KeepAliveMessage.encode_tlv_item(
                KeepAliveType.RTC_TIMESTAMP_TYPE, 8, self.rtc_timestamp_ms, "Q",
            )
        if self.timezone_offset_mn is not None:
            buffer += KeepAliveMessage.encode_tlv_item(
                KeepAliveType.TIME_ZONE_OFFSET_TYPE, 2, self.timezone_offset_mn, "h"
            )
        if self.keep_alive_interval_s is not None:
            buffer += KeepAliveMessage.encode_tlv_item(
                KeepAliveType.KEEP_ALIVE_INTERVAL_TYPE, 2, self.keep_alive_interval_s, "H",
            )

        return buffer


class KeepAliveServiceThread(Thread):
    def __init__(self, sink_manager, mqtt_wrapper,
                 keep_alive_interval_s=300,
                 keep_alive_timezone_offset_mn=0):
        """ Thread sending periodically keep alive messages to the network.

        Args:
            sink_manager: The sink manager to send sinks the keep alive messages.
            mqtt_wrapper: The mqtt wrapper to get access to queue level of the mqtt broker.
            keep_alive_interval_s (int): Default to 300 seconds.
                The interval in seconds between keep-alive messages.
            keep_alive_timezone_offset_mn (int): Default to 0.
                Time zone offset from UTC in minutes (-840 to +720) of the keep alive message.
        """
        Thread.__init__(self)

        # Daemonize thread to exit with full process
        self.daemon = True

        self.sink_manager = sink_manager
        self.mqtt_wrapper = mqtt_wrapper

        self.disconnected_sinks = set()  # All sinks that are detected as disconnected to the gateway
        self.connected_sinks = set()  #  All sinks that are detected as connected to the gateway

        self.keep_alive_interval_s = keep_alive_interval_s
        self.keep_alive_timezone_offset_mn = keep_alive_timezone_offset_mn

    def prepare_keep_alive_msg(self):
        """ Prepare and return a keep alive message. """
        rtc_timestamp_ms = None
        time_zone_offset = None

        rtc_timestamp_ms = int(time() * 1000)
        time_zone_offset = self.keep_alive_timezone_offset_mn

        gateway_status = int(self.mqtt_wrapper.connected)
        keep_alive_msg = KeepAliveMessage(KEEP_ALIVE_SERVICE_VERSION,
                                          gateway_status,
                                          rtc_timestamp_ms,
                                          time_zone_offset,
                                          self.keep_alive_interval_s)

        return keep_alive_msg

    def send_keep_alive_msg_to_sink(self, sink) -> bool:
        """
        Send the keep alive message to the network.
        Returns True if the keep alive message could be sent to the sink, False otherwise.

        Args:
            sink: Sink to send the keep alive message to.
        """
        retries_left = 3
        res = wmm.GatewayResultCode.GW_RES_UNKNOWN_ERROR

        while retries_left > 0 and res != wmm.GatewayResultCode.GW_RES_OK:
            retries_left -= 1
            keep_alive_message = self.prepare_keep_alive_msg()
            payload = keep_alive_message.encode_tlv()
            logging.debug("Send the following keep alive payload to sink %s: %s",
                          sink.sink_id, payload.hex())

            res = sink.send_data(
                dst=BROADCAST_ADDRESS,
                src_ep=KEEP_ALIVE_SRC_EP,
                dst_ep=KEEP_ALIVE_DST_EP,
                qos=0,
                initial_time=0,
                data=payload
            )
            if res != wmm.GatewayResultCode.GW_RES_OK and retries_left > 0:
                sleep(WM_MSG_RETRY_PERIOD_S)
                logging.debug("Retry sending the keep alive message that couldn't be sent to %s sink: %s. ",
                              sink.sink_id, res)

        if res != wmm.GatewayResultCode.GW_RES_OK:
            logging.error("Keep alive message couldn't be sent to %s sink: %s",
                          sink.sink_id, res)
            return False

        return True

    def wait_for_next_keep_alive_message_iteration(self, time_to_wait, start_timer=None):
        """ Wait for the next keep alive message iteration. """
        if start_timer:
            time_to_wait = max(time_to_wait - (time() - start_timer), 0)

        sleep(time_to_wait)

    def run(self):
        """ Main loop that send periodically keep alive message to the network. """
        while True:
            # Put a timer so that the message are periodic with a good precision
            start_timer = time()

            # Get current connected sinks
            current_sinks = set([sink.sink_id for sink in self.sink_manager.get_sinks()])
            current_connected_sinks = set()

            if not current_sinks:
                logging.error("No sinks are detected!")
                self.wait_for_next_keep_alive_message_iteration(self.keep_alive_interval_s)
                continue

            # Send keep alive messages to all sinks
            logging.info("Send a keep alive message to the network")
            for sink_id in current_sinks:
                if self.send_keep_alive_msg_to_sink(self.sink_manager.get_sink(sink_id)):
                    current_connected_sinks.add(sink_id)
                else:
                    self.disconnected_sinks.add(sink_id)

            # Find sinks that disappeared and those which reconnected during this iteration
            non_detected_sinks = self.connected_sinks.difference(current_sinks)
            reconnected_sinks = current_connected_sinks.intersection(self.disconnected_sinks)

            # Update sinks current status
            self.connected_sinks = current_connected_sinks
            self.disconnected_sinks.difference_update(current_connected_sinks)
            self.disconnected_sinks.update(non_detected_sinks)

            # If a sink reconnected, send 4 other keep alive messages in the next minutes
            if reconnected_sinks:
                messages_to_send = 4
                logging.debug("Sending keep alive messages more often to reconnected sinks: %s",
                              ' '.join(reconnected_sinks))
                self.wait_for_next_keep_alive_message_iteration(KEEP_ALIVE_MSG_RECONNECTION_PERIOD_S, start_timer)

                for _ in range(messages_to_send):
                    start_timer = time()
                    for sink_id in reconnected_sinks:
                        self.send_keep_alive_msg_to_sink(self.sink_manager.get_sink(sink_id))

                    self.wait_for_next_keep_alive_message_iteration(KEEP_ALIVE_MSG_RECONNECTION_PERIOD_S, start_timer)
            else:  # Else wait for sending the next keep alive message
                self.wait_for_next_keep_alive_message_iteration(self.keep_alive_interval_s, start_timer)
