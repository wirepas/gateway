# Copyright 2022 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import datetime
import logging
import os
import struct
import sys
from time import sleep, time
from uuid import getnode
from threading import Thread

from wirepas_gateway.dbus.dbus_client import BusClient
from wirepas_gateway.utils import ParserHelper

from wirepas_gateway import __version__ as transport_version
from wirepas_gateway import __pkg_name__

# This constant is the actual API level implemented by this rtc module (cf WP-RM-128)
IMPLEMENTED_API_VERSION = 2


BROADCAST_ADDRESS = 0xffffffff  # Broadcast
INITIAL_DELAY_MS = 0  # TODO : modify it to handle sink latency ?

# TODO, determine true Endpoints
RTC_SOURCE_EP = 78
RTC_DEST_EP = 78


class SynchronizationThread(Thread):

    def __init__(
        self,
        period,
        utc_to_local_conversion_s,
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
            try:
                self.utc_to_local_conversion_s = datetime.datetime.now(datetime.timezone.utc).astimezone().utcoffset().seconds
            except:
                return
        else:
            self.utc_to_local_conversion_s = utc_to_local_conversion_s

        self.sink_manager = sink_manager
        logging.info(f"Expected RTC sending period is set to {self.period}s")

        self.running = False

    def publish_time(self):
        """
        Publish the gateway time in the network.
        """
        timer = time()
        timer_ms = int(timer*1000)
        data_payload = bytes(struct.pack("<Ql",
                    timer_ms, self.utc_to_local_conversion_s))
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
            logging.info(f"time elapsed to send time through the gateway: {int((time()-start)*1000)}ms")

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
        logging.info("Version is: %s", transport_version)

        super(RtcService, self).__init__(
            c_extension=(settings.full_python is False),
            ignored_ep_filter=settings.ignored_endpoints_filter,
            **kwargs
        )

        self.gw_id = settings.gateway_id
        self.whitened_ep_filter = settings.whitened_endpoints_filter
        self.minimum_sink_cost = settings.buffering_minimal_sink_cost

        logging.info("Gateway started with id: %s", self.gw_id)

        self.synchronization_thread = SynchronizationThread(
            settings.rtc_synchronization_period_s,
            settings.utc_to_local_conversion_s,
            settings.rtc_timezone_abbreviation,
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
            timer=time()
            logging.info(f"Difference between rtc and expected sink time to be {int(timer*1000) - (int.from_bytes(data, 'little')+travel_time)}ms from node {src}")
            return  # rtc is not treated in the backend
        if self.whitened_ep_filter is not None and dst_ep in self.whitened_ep_filter:
            # Only publish payload size but not the payload
            logging.debug("Filtering payload data")
            data_size = data.__len__()
            data = None
        else:
            data_size = None

        sink = self.sink_manager.get_sink(sink_id)
        if sink is None:
            # It can happen at sink connection as messages can be received
            # before sinks are identified
            logging.info(
                "Message received from unknown sink at the moment %s", sink_id
            )
            return


    def on_stack_started(self, name):
        logging.debug("Sink started: %s", name)

    def on_stack_stopped(self, name):
        logging.debug("Sink stopped: %s", name)

    def on_sink_connected(self, name):
        logging.info("Sink connected, sending new configs")
        sink = self.sink_manager.get_sink(name)
        if sink is not None:
            logging.info(
                "Initialize sinkCost of sink {} to minimum {}".format(
                    name, self.minimum_sink_cost
                )
            )
            try:
                sink.cost = self.minimum_sink_cost
            except ValueError:
                logging.debug("Cannot set cost, probably not a sink")

    def on_sink_disconnected(self, name):
        logging.info("Sink disconnected, sending new configs")

def parse_setting_list(list_setting):
    """ This function parse ep list specified from setting file or cmd line

    Input list has following format [1, 5, 10-15] as a string or list of string
    and is expended as a single list [1, 5, 10, 11, 12, 13, 14, 15]

    Args:
        list_setting(str or list): the list from setting file or cmd line.

    Returns: A single list of ep
    """
    if isinstance(list_setting, str):
        # List is a string from cmd line
        list_setting = list_setting.replace("[", "")
        list_setting = list_setting.replace("]", "")
        list_setting = list_setting.split(",")

    single_list = []
    for ep in list_setting:
        # Check if ep is directly an int
        if isinstance(ep, int):
            if ep < 0 or ep > 255:
                raise SyntaxError("EP out of bound")
            single_list.append(ep)
            continue

        # Check if ep is a single ep as string
        try:
            ep = int(ep)
            if ep < 0 or ep > 255:
                raise SyntaxError("EP out of bound")
            single_list.append(ep)
            continue
        except ValueError:
            # Probably a range
            pass

        # Check if ep is a range
        try:
            ep = ep.replace("'", "")
            lower, upper = ep.split("-")
            lower = int(lower)
            upper = int(upper)
            if lower > upper or lower < 0 or upper > 255:
                raise SyntaxError("Wrong EP range value")

            single_list += list(range(lower, upper + 1))
        except (AttributeError, ValueError):
            raise SyntaxError("Wrong EP range format")

    return single_list


def _check_duplicate(args, old_param, new_param, default):
    old_param_val = getattr(args, old_param, default)
    new_param_val = getattr(args, new_param, default)
    if new_param_val == old_param_val:
        # Nothing to update
        return

    if old_param_val != default:
        # Old param is set, check if new_param is also set
        if new_param_val == default:
            setattr(args, new_param, old_param_val)
            logging.warning(
                "Param %s is deprecated, please use %s instead", old_param, new_param
            )
        else:
            logging.error(
                "Param %s and %s cannot be set at the same time", old_param, new_param
            )
            exit()


def _update_parameters(settings):
    """
    Function to handle the backward compatibility with old parameters name
    Args:
        settings: Full parameters

    Returns: None
    """

    _check_duplicate(settings, "gwid", "gateway_id", None)

    if settings.gateway_id is None:
        settings.gateway_id = str(getnode())

    # Parse EP list that should not be published
    if settings.ignored_endpoints_filter:
        try:
            settings.ignored_endpoints_filter = parse_setting_list(
                settings.ignored_endpoints_filter
            )
            logging.debug("Ignored endpoints are: %s", settings.ignored_endpoints_filter)
        except SyntaxError as e:
            logging.error("Wrong format for ignored_endpoints_filter EP list (%s)", e)
            exit()

    if settings.whitened_endpoints_filter:
        try:
            settings.whitened_endpoints_filter = parse_setting_list(
                settings.whitened_endpoints_filter
            )
            logging.debug(
                "Whitened endpoints are: {}".format(settings.whitened_endpoints_filter)
            )
        except SyntaxError as e:
            logging.error("Wrong format for whitened_endpoints_filter EP list (%s)", e)
            exit()


def _check_parameters(settings):
    try:
        if set(settings.ignored_endpoints_filter) & set(
            settings.whitened_endpoints_filter
        ):
            logging.error("Some endpoints are both ignored and whitened")
            exit()
    except TypeError:
        # One of the filter list is None
        pass


def main():
    """
        Main service for rtc service module

    """
    parse = ParserHelper(
        description="Wirepas Gateway Transport service arguments",
        version=transport_version,
    )

    parse.add_file_settings()
    parse.add_gateway_config()
    parse.add_filtering_config()
    parse.add_buffering_settings()
    parse.add_deprecated_args()
    parse.add_rtc_settings()

    settings = parse.settings()

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

    _update_parameters(settings)

    _check_parameters(settings)

    RtcService(settings=settings).run()


if __name__ == "__main__":
    main()
