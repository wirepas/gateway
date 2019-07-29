# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import logging
import os
from time import time
from uuid import getnode
from threading import Thread

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

from wirepas_gateway import __version__ as transport_version
from wirepas_gateway import __pkg_name__

# This constant is the actual API level implemented by this transport module (cf WP-RM-128)
IMPLEMENTED_API_VERSION = 1


class TransportService(BusClient):
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

        super(TransportService, self).__init__(
            logger=logger,
            c_extension=(settings.full_python is False),
            ignored_ep_filter=settings.ignored_endpoints_filter,
            **kwargs
        )

        self.gw_id = settings.gateway_id
        self.gw_model = settings.gateway_model
        self.gw_version = settings.gateway_version

        self.whitened_ep_filter = settings.whitened_endpoints_filter

        last_will_topic = TopicGenerator.make_status_topic(self.gw_id)
        last_will_message = wirepas_messaging.gateway.api.StatusEvent(
            self.gw_id, GatewayState.OFFLINE
        ).payload

        self.mqtt_wrapper = MQTTWrapper(
            settings,
            self.logger,
            self._on_mqtt_wrapper_termination_cb,
            self._on_connect,
            last_will_topic,
            last_will_message,
        )

        self.mqtt_wrapper.start()

        self.logger.info("Gateway started with id: %s", self.gw_id)

    def _on_mqtt_wrapper_termination_cb(self):
        """
        Callback used to be informed when the MQTT wrapper has exited
        It is not a normal situation and better to exit the program
        to have a change to restart from a clean session
        """
        self.logger.error("MQTT wrapper ends. Terminate the program")
        self.stop_dbus_client()

    def _set_status(self):
        event_online = wirepas_messaging.gateway.api.StatusEvent(
            self.gw_id, GatewayState.ONLINE
        )

        topic = TopicGenerator.make_status_topic(self.gw_id)

        self.mqtt_wrapper.publish(topic, event_online.payload, qos=1, retain=True)

    def _on_connect(self):
        # Register for get gateway info
        topic = TopicGenerator.make_get_gateway_info_request_topic(self.gw_id)
        self.mqtt_wrapper.subscribe(topic, self._on_get_gateway_info_cmd_received)

        # Register for get configs request
        topic = TopicGenerator.make_get_configs_request_topic(self.gw_id)
        self.mqtt_wrapper.subscribe(topic, self._on_get_configs_cmd_received)

        # Register for set config request for any sink
        topic = TopicGenerator.make_set_config_request_topic(self.gw_id)
        self.mqtt_wrapper.subscribe(topic, self._on_set_config_cmd_received)

        # Register for send data request for any sink on the gateway
        topic = TopicGenerator.make_send_data_request_topic(self.gw_id)
        self.logger.debug("Subscribing to: %s", topic)
        # It is important to have a qos of 2 and also from the publisher as 1 could generate
        # duplicated packets and we don't know the consequences on end
        # application
        self.mqtt_wrapper.subscribe(topic, self._on_send_data_cmd_received, qos=2)

        # Register for otap commands for any sink on the gateway
        topic = TopicGenerator.make_otap_status_request_topic(self.gw_id)
        self.mqtt_wrapper.subscribe(topic, self._on_otap_status_request_received)

        topic = TopicGenerator.make_otap_load_scratchpad_request_topic(self.gw_id)
        self.mqtt_wrapper.subscribe(
            topic, self._on_otap_upload_scratchpad_request_received
        )

        topic = TopicGenerator.make_otap_process_scratchpad_request_topic(self.gw_id)
        self.mqtt_wrapper.subscribe(
            topic, self._on_otap_process_scratchpad_request_received
        )

        self._set_status()

        self.logger.info("MQTT connected!")

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

        if self.whitened_ep_filter is not None and dst_ep in self.whitened_ep_filter:
            # Only publish payload size but not the payload
            self.logger.debug("Filtering payload data")
            data_size = data.__len__()
            data = None
        else:
            data_size = None

        event = wirepas_messaging.gateway.api.ReceivedDataEvent(
            gw_id=self.gw_id,
            sink_id=sink_id,
            rx_time_ms_epoch=timestamp,
            src=src,
            dst=dst,
            src_ep=src_ep,
            dst_ep=dst_ep,
            travel_time_ms=travel_time,
            qos=qos,
            data=data,
            data_size=data_size,
            hop_count=hop_count,
        )

        sink = self.sink_manager.get_sink(sink_id)
        if sink is None:
            # It can happen at sink connection as messages can be received
            # before sinks are identified
            self.logger.info(
                "Message received from unknown sink at the moment %s", sink_id
            )
            return

        network_address = sink.get_network_address()

        topic = TopicGenerator.make_received_data_topic(
            self.gw_id, sink_id, network_address, src_ep, dst_ep
        )
        self.logger.debug("Sending data to: %s", topic)
        # Set qos to 1 to avoid loading too much the broker
        # unique id in event header can be used for duplicate filtering in
        # backends
        self.mqtt_wrapper.publish(topic, event.payload, qos=1)

    def on_stack_started(self, name):
        sink = self.sink_manager.get_sink(name)
        if sink is None:
            self.logger.error("Sink started %s error: unknown sink", name)
            return

        # Generate a setconfig answer with req_id of 0
        response = wirepas_messaging.gateway.api.SetConfigResponse(
            0, self.gw_id, GatewayResultCode.GW_RES_OK, sink.sink_id, sink.read_config()
        )
        topic = TopicGenerator.make_set_config_response_topic(self.gw_id, sink.sink_id)
        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    def _send_asynchronous_get_configs_response(self):
        # Create a list of different sink configs
        configs = []
        for sink in self.sink_manager.get_sinks():
            config = sink.read_config()
            if config is not None:
                configs.append(config)

        # Generate a setconfig answer with req_id of 0 as not from
        # a real request
        response = wirepas_messaging.gateway.api.GetConfigsResponse(
            0, self.gw_id, GatewayResultCode.GW_RES_OK, configs
        )
        topic = TopicGenerator.make_get_configs_response_topic(self.gw_id)

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

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

    def on_sink_connected(self, name):
        self.logger.info("Sink connected, sending new configs")
        self._send_asynchronous_get_configs_response()

    def on_sink_disconnected(self, name):
        self.logger.info("Sink disconnected, sending new configs")
        self._send_asynchronous_get_configs_response()

    @deferred_thread
    def _on_send_data_cmd_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        self.logger.info("Request to send data")
        try:
            request = wirepas_messaging.gateway.api.SendDataRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return

        # Get the sink-id from topic
        _, sink_id = TopicParser.parse_send_data_topic(message.topic)

        self.logger.debug("Request for sink %s", sink_id)

        sink = self.sink_manager.get_sink(sink_id)
        if sink is not None:
            if request.hop_limit > self.MAX_HOP_LIMIT:
                res = GatewayResultCode.INVALID_MAX_HOP_COUNT
            else:
                res = sink.send_data(
                    request.destination_address,
                    request.source_endpoint,
                    request.destination_endpoint,
                    request.qos,
                    request.initial_delay_ms,
                    request.data_payload,
                    request.is_unack_csma_ca,
                    request.hop_limit,
                )
        else:
            self.logger.warning("No sink with id: %s", sink_id)
            # No sink with  this id
            res = GatewayResultCode.GW_RES_INVALID_SINK_ID

        # Answer to backend
        response = wirepas_messaging.gateway.api.SendDataResponse(
            request.req_id, self.gw_id, res, sink_id
        )
        topic = TopicGenerator.make_send_data_response_topic(self.gw_id, sink_id)

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    def _on_get_configs_cmd_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        self.logger.info("Config request received")
        try:
            request = wirepas_messaging.gateway.api.GetConfigsRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return

        # Create a list of different sink configs
        configs = []
        for sink in self.sink_manager.get_sinks():
            config = sink.read_config()
            if config is not None:
                configs.append(config)

        response = wirepas_messaging.gateway.api.GetConfigsResponse(
            request.req_id, self.gw_id, GatewayResultCode.GW_RES_OK, configs
        )
        topic = TopicGenerator.make_get_configs_response_topic(self.gw_id)

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    def _on_get_gateway_info_cmd_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        """
        This function doesn't need the decorator @deferred_thread as request is handled
        without I/O
        """
        self.logger.info("Gateway info request received")
        try:
            request = wirepas_messaging.gateway.api.GetGatewayInfoRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return

        response = wirepas_messaging.gateway.api.GetGatewayInfoResponse(
            request.req_id,
            self.gw_id,
            GatewayResultCode.GW_RES_OK,
            current_time_s_epoch=int(time()),
            gateway_model=self.gw_model,
            gateway_version=self.gw_version,
            implemented_api_version=IMPLEMENTED_API_VERSION,
        )

        topic = TopicGenerator.make_get_gateway_info_response_topic(self.gw_id)
        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    def _on_set_config_cmd_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        self.logger.info("Set config request received")
        try:
            request = wirepas_messaging.gateway.api.SetConfigRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return

        self.logger.debug("Set sink config: %s", request)
        sink = self.sink_manager.get_sink(request.sink_id)
        if sink is not None:
            res = sink.write_config(request.new_config)
            new_config = sink.read_config()
        else:
            res = GatewayResultCode.GW_RES_INVALID_SINK_ID
            new_config = None

        response = wirepas_messaging.gateway.api.SetConfigResponse(
            request.req_id, self.gw_id, res, request.sink_id, new_config
        )
        topic = TopicGenerator.make_set_config_response_topic(
            self.gw_id, request.sink_id
        )

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    def _on_otap_status_request_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        self.logger.info("OTAP status request received")
        try:
            request = wirepas_messaging.gateway.api.GetScratchpadStatusRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return

        sink = self.sink_manager.get_sink(request.sink_id)
        if sink is not None:
            d = sink.get_scratchpad_status()

            response = wirepas_messaging.gateway.api.GetScratchpadStatusResponse(
                request.req_id,
                self.gw_id,
                GatewayResultCode.GW_RES_OK,
                request.sink_id,
                d["stored_scartchpad"],
                d["stored_status"],
                d["stored_type"],
                d["processed_scartchpad"],
                d["firmware_area_id"],
            )
        else:
            response = wirepas_messaging.gateway.api.GetScratchpadStatusResponse(
                request.req_id,
                self.gw_id,
                GatewayResultCode.GW_RES_INVALID_SINK_ID,
                request.sink_id,
            )

        topic = TopicGenerator.make_otap_status_response_topic(
            self.gw_id, request.sink_id
        )

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    def _on_otap_upload_scratchpad_request_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        self.logger.info("OTAP upload request received")
        try:
            request = wirepas_messaging.gateway.api.UploadScratchpadRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return

        self.logger.info("OTAP upload request received for %s", request.sink_id)

        sink = self.sink_manager.get_sink(request.sink_id)
        if sink is not None:
            res = sink.upload_scratchpad(request.seq, request.scratchpad)
        else:
            res = GatewayResultCode.GW_RES_INVALID_SINK_ID

        response = wirepas_messaging.gateway.api.UploadScratchpadResponse(
            request.req_id, self.gw_id, res, request.sink_id
        )

        topic = TopicGenerator.make_otap_upload_scratchpad_response_topic(
            self.gw_id, request.sink_id
        )

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    def _on_otap_process_scratchpad_request_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        self.logger.info("OTAP process request received")
        try:
            request = wirepas_messaging.gateway.api.ProcessScratchpadRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return

        sink = self.sink_manager.get_sink(request.sink_id)
        if sink is not None:
            res = sink.process_scratchpad()
        else:
            res = GatewayResultCode.GW_RES_INVALID_SINK_ID

        response = wirepas_messaging.gateway.api.ProcessScratchpadResponse(
            request.req_id, self.gw_id, res, request.sink_id
        )

        topic = TopicGenerator.make_otap_process_scratchpad_response_topic(
            self.gw_id, request.sink_id
        )

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)


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

    TransportService(settings=settings, logger=logger).run()


if __name__ == "__main__":
    main()
