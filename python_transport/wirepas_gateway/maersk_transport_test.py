# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import logging
import os
from time import time
from uuid import getnode
from threading import Thread
import time

import wirepas_messaging
from wirepas_gateway.dbus.dbus_client import BusClient
from wirepas_gateway.protocol.topic_helper import TopicGenerator, TopicParser
from wirepas_gateway.protocol.mqtt_wrapper import MQTTWrapper
from wirepas_gateway.utils import ParserHelper
from wirepas_gateway.utils import LoggerHelper
from wirepas_messaging.gateway.api import (
    GatewayResultCode,
    GatewayState,
    GatewayAPIParsingException,
)

import maersk_request_parser

from wirepas_gateway import __version__ as transport_version
from wirepas_gateway import __pkg_name__

# This constant is the actual API level implemented by this transport module (cf WP-RM-128)
IMPLEMENTED_API_VERSION = 1


class TransportService():
    """
    Implementation of gateway to backend protocol

    Get all the events from DBUS and publih it with right format
    for gateways
    """

    # Maximum hop limit to send a packet is limited to 15 by API (4 bits)
    MAX_HOP_LIMIT = 15

    def __init__(self, settings, logger=None, **kwargs):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("Version is: %s", transport_version)

        self.gw_id = settings.gateway_id
        self.gw_model = settings.gateway_model
        self.gw_version = settings.gateway_version

        self.whitened_ep_filter = settings.whitened_endpoints_filter

        last_will_topic = TopicGenerator.make_status_topic(self.gw_id)
        last_will_message = wirepas_messaging.gateway.api.StatusEvent(
            self.gw_id, GatewayState.OFFLINE
        ).payload

        settings.gateway_id = settings.gateway_id + "-test"
        self.mqtt_wrapper = MQTTWrapper(
            settings,
            self.logger,
            self._on_mqtt_wrapper_termination_cb,
            self._on_connect,
            last_will_topic,
            last_will_message,
        )

        self.mqtt_wrapper.start()

        self.logger.info("Test started with target: %s", self.gw_id)

    def _on_mqtt_wrapper_termination_cb(self):
        """
        Callback used to be informed when the MQTT wrapper has exited
        It is not a normal situation and better to exit the program
        to have a change to restart from a clean session
        """
        self.logger.error("MQTT wrapper ends. Terminate the program")
        self.stop_dbus_client()

    def _on_connect(self):
        self.logger.info("MQTT connect!")

        # Maersk requests
        self.mqtt_wrapper.subscribe("gw-response/exec_cmd/" + self.gw_id, self._on_gw_response)

        try:
            # send Req
            message = wirepas_messaging.gateway.GenericMessage()
            message.customer.customer_name = "Maersk"

            message.customer.request.header.time_to_live_epoch_ms = int(time.time() * 1000) + 1000
            message.customer.request.gateway_req.header.req_id = 22
            message.customer.request.gateway_req.gw_status_req.SetInParent()

            self.mqtt_wrapper.publish("gw-request/exec_cmd/" + self.gw_id, message.SerializeToString(), qos=2)
            self.logger.info("published!")

        except Exception as e:
            self.logger.error(str(e))


    def deferred_thread(fn):
        """
        Decorator to handle a request on its own Thread
        to avoid blocking the calling Thread on I/O.
        It creates a new Thread but it shouldn't impact the performances
        as requests are not supposed to be really frequent (few per seconds)
        """

        def wrapper(*args, **kwargs):
            thread = Thread(target=fn, args=args, kwargs=kwargs)
            thread.start()
            return thread

        return wrapper 

    @deferred_thread
    def _on_gw_response(self, client, userdata, message):
        # pylint: disable=unused-argument
        self.logger.info("Gateway response received")

        try:
            msg = wirepas_messaging.gateway.GenericMessage()
            msg.ParseFromString(message.payload)

            # Check all the optional fields
            if not msg.HasField('customer'):
                raise MaerskParsingException("Cannot parse customer field")
            customer = msg.customer

            if not customer.HasField('response'):
                raise MaerskParsingException("Cannot parse response field")
            response = customer.response

            if not response.HasField('gateway_resp'):
                raise MaerskParsingException("Cannot parse gateway_resp field")
            gateway_resp = response.gateway_resp

            if not gateway_resp.HasField('gw_status_resp'):
                raise MaerskParsingException("response not implemented")


            self.logger.info(" Customer_name %s, epoch %d, request id %d",
                customer.customer_name,
                customer.response.header.gateway_epoch_ms, 
                customer.response.gateway_resp.header.req_id
            )
            self.logger.info(" Gateway id %s, result %d",
                customer.response.gateway_resp.header.gw_id,
                customer.response.gateway_resp.header.res
            )
            self.logger.info(" App %s, wirepas %s, IMSI %d", 
                customer.response.gateway_resp.gw_status_resp.app_software,
                customer.response.gateway_resp.gw_status_resp.wirepas_software,
                customer.response.gateway_resp.gw_status_resp.imsi
            )

        except Exception as e:
            self.logger.error(str(e))


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


def _check_duplicate(args, old_param, new_param, default, logger):
    old_param_val = getattr(args, old_param, default)
    new_param_val = getattr(args, new_param, default)
    if new_param_val == old_param_val:
        # Nothing to update
        return

    if old_param_val != default:
        # Old param is set, check if new_param is also set
        if new_param_val == default:
            setattr(args, new_param, old_param_val)
            logger.warning(
                "Param %s is deprecated, please use %s instead", old_param, new_param
            )
        else:
            logger.error(
                "Param %s and %s cannot be set at the same time", old_param, new_param
            )
            exit()


def _update_parameters(settings, logger):
    """
    Function to handle the backward compatibility with old parameters name
    Args:
        settings: Full parameters

    Returns: None
    """

    _check_duplicate(settings, "host", "mqtt_hostname", None, logger)
    _check_duplicate(settings, "port", "mqtt_port", 8883, logger)
    _check_duplicate(settings, "username", "mqtt_username", None, logger)
    _check_duplicate(settings, "password", "mqtt_password", None, logger)
    _check_duplicate(settings, "tlsfile", "mqtt_certfile", None, logger)
    _check_duplicate(
        settings, "unsecure_authentication", "mqtt_force_unsecure", False, logger
    )
    _check_duplicate(settings, "gwid", "gateway_id", None, logger)

    if settings.gateway_id is None:
        settings.gateway_id = str(getnode())

    # Parse EP list that should not be published
    if settings.ignored_endpoints_filter is not None:
        try:
            settings.ignored_endpoints_filter = parse_setting_list(
                settings.ignored_endpoints_filter
            )
            logger.debug("Ignored endpoints are: %s", settings.ignored_endpoints_filter)
        except SyntaxError as e:
            logger.error("Wrong format for ignored_endpoints_filter EP list (%s)", e)
            exit()

    if settings.whitened_endpoints_filter is not None:
        try:
            settings.whitened_endpoints_filter = parse_setting_list(
                settings.whitened_endpoints_filter
            )
            logger.debug(
                "Whitened endpoints are: {}".format(settings.whitened_endpoints_filter)
            )
        except SyntaxError as e:
            logger.error("Wrong format for whitened_endpoints_filter EP list (%s)", e)
            exit()


def _check_parameters(settings, logger):
    if settings.mqtt_force_unsecure and settings.mqtt_certfile:
        # If tls cert file is provided, unsecure authentication cannot
        # be set
        logger.error("Cannot give certfile and disable secure authentication")
        exit()

    try:
        if set(settings.ignored_endpoints_filter) & set(
            settings.whitened_endpoints_filter
        ):
            logger.error("Some endpoints are both ignored and whitened")
            exit()
    except TypeError:
        # One of the filter list is None
        pass


def main():
    """
        Main service for transport module

    """
    parse = ParserHelper(
        description="Wirepas Gateway Transport service arguments",
        version=transport_version,
    )

    parse.add_file_settings()
    parse.add_mqtt()
    parse.add_gateway_config()
    parse.add_filtering_config()
    parse.add_deprecated_args()

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

    log = LoggerHelper(module_name=__pkg_name__, level=debug_level)
    logger = log.setup()

    _update_parameters(settings, logger)
    # after this stage, mqtt deprecated argument cannot be used

    _check_parameters(settings, logger)

    TransportService(settings=settings, logger=logger)
    time.sleep(5) 


if __name__ == "__main__":
    main()
