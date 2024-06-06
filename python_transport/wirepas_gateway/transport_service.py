# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import logging
import os
import sys
import wirepas_mesh_messaging as wmm
from time import time, sleep
from uuid import getnode
from threading import Lock, Thread

from wirepas_gateway.dbus.dbus_client import BusClient
from wirepas_gateway.protocol.topic_helper import TopicGenerator, TopicParser
from wirepas_gateway.protocol.mqtt_wrapper import MQTTWrapper
from wirepas_gateway.utils import ParserHelper

from wirepas_gateway import __version__ as transport_version
from wirepas_gateway import __pkg_name__

# This constant is the actual API level implemented by this transport module (cf WP-RM-128)
IMPLEMENTED_API_VERSION = 2


class ConnectionToBackendMonitorThread(Thread):

    # Maximum cost to disable traffic
    SINK_COST_HIGH = 254

    def __init__(
        self,
        period,
        mqtt_wrapper,
        sink_manager,
        minimum_sink_cost,
        max_buffered_packets,
        max_delay_without_publish,
    ):
        """
        Thread monitoring the connection with the MQTT broker.
        Connection status is monitored thanks to the number of
        messages pushed to the mqtt client queue but not published.
        And the latest successfully published packet is also monitored.
        Mqtt connection is not used as a trigger as it may modify too often
        the sink cost with an unstable connection that would be counterproductive.

        Args:
            period: the period to check the buffer status
            mqtt_wrapper: the mqtt wrapper to get access to queue level
            sink_manager: the sink manager to modify sink cost of all sinks
            minimum_sink_cost: the minimum sink cost for sinks on this gateway
            max_buffered_packets: the maximum number of packets that can be buffered before
                                  rising the sink costs
            max_delay_without_publish: the maximum delay without any successful publish (with
                                       something in the queue before rising the sink costs
        """
        Thread.__init__(self)

        # Daemonize thread to exit with full process
        self.daemon = True

        # How often to check the queue
        self.period = period
        self.mqtt_wrapper = mqtt_wrapper
        self.sink_manager = sink_manager

        self.running = False
        self.disconnected = False

        # Get parameters for black hole algorithm detection
        self.minimum_sink_cost = minimum_sink_cost
        self.max_buffered_packets = max_buffered_packets
        self.max_delay_without_publish = max_delay_without_publish

    def _set_sinks_cost(self, cost):
        for sink in self.sink_manager.get_sinks():
            sink.cost = cost

    def _set_sinks_cost_high(self):
        self._set_sinks_cost(self.SINK_COST_HIGH)

    def _set_sinks_cost_low(self):
        self._set_sinks_cost(self.minimum_sink_cost)

    def _is_publish_delay_over(self):
        if self.max_delay_without_publish <= 0:
            # No max delay set, not enabled
            return False

        return (
            self.mqtt_wrapper.publish_waiting_time_s > self.max_delay_without_publish
        )

    def _is_buffer_threshold_reached(self):
        if self.max_buffered_packets <= 0:
            # Useless check as mechanism is disabled if max is 0
            return False

        return self.mqtt_wrapper.publish_queue_size > self.max_buffered_packets

    def run(self):
        """
        Main loop that check periodically the status of the published queue and compare
        it to threshold set when starting Transport
        """

        # Initialize already detected sinks
        self._set_sinks_cost_low()

        self.running = True

        while self.running:
            if not self.disconnected:
                # Check if a condition to declare "back hole" is met
                if self._is_publish_delay_over() or self._is_buffer_threshold_reached():
                    logging.info("Increasing sink cost of all sinks")
                    logging.debug(
                        "Last publish: %s Queue Size %s",
                        self.mqtt_wrapper.publish_waiting_time_s,
                        self.mqtt_wrapper.publish_queue_size,
                    )

                    self._set_sinks_cost_high()
                    self.disconnected = True
            else:
                if self.mqtt_wrapper.publish_queue_size == 0:
                    # Network is back, put the connection back
                    logging.info(
                        "Connection is back, decreasing sink cost of all sinks"
                    )
                    self._set_sinks_cost_low()
                    self.disconnected = False

            # Wait for period
            sleep(self.period)

    def stop(self):
        """
        Stop the black hole monitoring thread
        """
        self.running = False

    def initialize_sink(self, name):
        """
        Initialize sink cost according to current connection state
        Args:
            name: name of sink to initialize
        """
        sink = self.sink_manager.get_sink(name)

        logging.info("Initialize sinkCost of sink %s", name)
        if sink is not None:
            if self.disconnected:
                sink.cost = self.SINK_COST_HIGH
            else:
                sink.cost = self.minimum_sink_cost


class TransportService(BusClient):
    """
    Implementation of gateway to backend protocol

    Get all the events from DBUS and publih it with right format
    for gateways
    """

    # Maximum hop limit to send a packet is limited to 15 by API (4 bits)
    MAX_HOP_LIMIT = 15

    # Period in s to check for black hole issue
    MONITORING_BUFFERING_PERIOD_S = 1

    def __init__(self, settings, **kwargs):
        logging.info("Version is: %s", transport_version)

        super(TransportService, self).__init__(
            c_extension=(settings.full_python is False),
            ignored_ep_filter=settings.ignored_endpoints_filter,
            **kwargs
        )

        self.gw_id = settings.gateway_id
        self.gw_model = settings.gateway_model
        self.gw_version = settings.gateway_version

        self.whitened_ep_filter = settings.whitened_endpoints_filter

        last_will_topic = TopicGenerator.make_status_topic(self.gw_id)
        last_will_message = wmm.StatusEvent(
            self.gw_id, wmm.GatewayState.OFFLINE,
            gateway_model=self.gw_model,
            gateway_version=self.gw_version
        ).payload

        self.mqtt_wrapper = MQTTWrapper(
            settings,
            self._on_mqtt_wrapper_termination_cb,
            self._on_connect,
            last_will_topic,
            last_will_message,
        )

        self.mqtt_wrapper.start()

        logging.info("Gateway started with id: %s", self.gw_id)

        self.monitoring_thread = None
        self.minimum_sink_cost = settings.buffering_minimal_sink_cost

        if settings.buffering_max_buffered_packets > 0 or settings.buffering_max_delay_without_publish > 0:
            logging.info(
                " Black hole detection enabled: max_packets=%s packets, max_delay=%s",
                settings.buffering_max_buffered_packets,
                settings.buffering_max_delay_without_publish,
            )
            # Create and start a monitoring thread for black hole issue
            self.monitoring_thread = ConnectionToBackendMonitorThread(
                self.MONITORING_BUFFERING_PERIOD_S,
                self.mqtt_wrapper,
                self.sink_manager,
                settings.buffering_minimal_sink_cost,
                settings.buffering_max_buffered_packets,
                settings.buffering_max_delay_without_publish,
            )
            self.monitoring_thread.start()

        if settings.debug_incr_data_event_id:
            self.data_event_id = 0
        else:
            self.data_event_id = None

        # Flag to know if updating the status is already scheduled
        self._is_update_status_scheduled = False
        self._status_lock = Lock()

        self._last_status_config = None

    def _on_mqtt_wrapper_termination_cb(self):
        """
        Callback used to be informed when the MQTT wrapper has exited
        It is not a normal situation and better to exit the program
        to have a change to restart from a clean session
        """
        logging.error("MQTT wrapper ends. Terminate the program")
        self.stop_dbus_client()

    def _set_status(self):
        # Create a list of different sink configs
        partial_status = False
        configs = []
        for sink in self.sink_manager.get_sinks():
            config, partial = sink.read_config()
            partial_status |= partial
            if config is not None:
                configs.append(config)

        if partial_status:
            # Some part of the status were read from cache value
            logging.warning("Some value were not up to date")

        # Publish only if something has changed
        if self._last_status_config is not None and \
            self._last_status_config == configs:
                logging.info("No new status to publish")
                return

        event_online = wmm.StatusEvent(
                            self.gw_id,
                            wmm.GatewayState.ONLINE,
                            sink_configs=configs,
                            gateway_model=self.gw_model,
                            gateway_version=self.gw_version,
                            )

        topic = TopicGenerator.make_status_topic(self.gw_id)

        self.mqtt_wrapper.publish(topic, event_online.payload, qos=1, retain=True)

        self._last_status_config = configs.copy()

        return partial_status

    def _update_status(self):
        # First check if an update is about to be sent to avoid
        # multiple updates in a short period (0.5s)
        with self._status_lock:
            if self._is_update_status_scheduled:
                # Update is already scheduled, so our modification
                # will be handled soon
                logging.debug("Update already scheduled")
                return
            else:
                logging.debug("Update not scheduled yet")
                self._is_update_status_scheduled = True

        def set_status_after_delay(delay_s):
            sleep(delay_s)
            attempt = 0
            logging.debug("Time to update the status")
            if self._set_status():
                # Status is partial, retry few times until we have valid one
                delay_s = 2
                while attempt < 5:
                    sleep(delay_s)
                    logging.debug("New attempt to publish status")
                    if not self._set_status():
                        # Successful update
                        break

                    attempt += 1
                    delay_s *= 2

            if attempt == 5:
                logging.error("Not able to read a full status")
            self._is_update_status_scheduled = False

        # We are here as there was no update scheduled yet.
        # Wait a bit in case something else is changing
        thread = Thread(target=set_status_after_delay, args=[0.5])
        thread.start()

    def update_gateway_status_dec(fn):
        """
        Decorator to update the gateway status when needed
        """
        def wrapper(self, *args, **kwargs):
            fn(self, *args, **kwargs)
            logging.debug("Updating gw status for %s", fn)
            self._update_status()
            return

        return wrapper

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
        logging.debug("Subscribing to: %s", topic)
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

        topic = TopicGenerator.make_otap_set_target_scratchpad_request_topic(self.gw_id)
        self.mqtt_wrapper.subscribe(
            topic, self._on_otap_set_target_scratchpad_request_received
        )

        # Reset our cached value to be sure the status is published again
        # If we are here, it means that we were disconnected and our last_will
        # status was sent
        self._last_status_config = None
        self._set_status()

        logging.info("MQTT connected!")

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

        network_address = sink.get_network_address()

        event = wmm.ReceivedDataEvent(
            event_id=self.data_event_id,
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
            network_address=network_address,
        )

        topic = TopicGenerator.make_received_data_topic(
            self.gw_id, sink_id, network_address, src_ep, dst_ep
        )
        logging.debug("Uplink traffic: %s | %s", topic, event.event_id)

        # No need to protect data_event_id as on_data_received is always
        # called from same thread
        if self.data_event_id is not None:
            self.data_event_id += 1

        # Set qos to 1 to avoid loading too much the broker
        # unique id in event header can be used for duplicate filtering in
        # backends
        self.mqtt_wrapper.publish(topic, event.payload, qos=1)

    @update_gateway_status_dec
    def on_stack_started(self, name):
        logging.debug("Sink started: %s", name)
        # Generate a setconfig answer with req_id of 0
        self._send_asynchronous_set_config_response(name)

    @update_gateway_status_dec
    def on_stack_stopped(self, name):
        logging.debug("Sink stopped: %s", name)
        # Generate a setconfig answer with req_id of 0
        self._send_asynchronous_set_config_response(name)

    def _send_asynchronous_set_config_response(self, name):
        sink = self.sink_manager.get_sink(name)
        if sink is None:
            logging.error("Sink %s error: unknown sink", name)
            return

        config, _ = sink.read_config()
        response = wmm.SetConfigResponse(
            0,
            self.gw_id,
            wmm.GatewayResultCode.GW_RES_OK,
            sink.sink_id,
            config,
        )
        topic = TopicGenerator.make_set_config_response_topic(self.gw_id, sink.sink_id)
        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    def _send_asynchronous_get_configs_response(self):
        # Create a list of different sink configs
        configs = []
        for sink in self.sink_manager.get_sinks():
            config, _ = sink.read_config()
            if config is not None:
                configs.append(config)

        # Generate a setconfig answer with req_id of 0 as not from
        # a real request
        response = wmm.GetConfigsResponse(
            0, self.gw_id, wmm.GatewayResultCode.GW_RES_OK, configs
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

    @update_gateway_status_dec
    def on_sink_connected(self, name):
        logging.info("Sink connected, sending new configs")
        if self.monitoring_thread is not None:
            # Black hole algorithm in place do not initialize here the cost
            self.monitoring_thread.initialize_sink(name)
        else:
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

        self._send_asynchronous_get_configs_response()

    @update_gateway_status_dec
    def on_sink_disconnected(self, name):
        logging.info("Sink disconnected, sending new configs")
        self._send_asynchronous_get_configs_response()

    @deferred_thread
    def _on_send_data_cmd_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        try:
            request = wmm.SendDataRequest.from_payload(message.payload)
        except wmm.GatewayAPIParsingException as e:
            logging.error(str(e))
            return

        # Get the sink-id from topic
        _, sink_id = TopicParser.parse_send_data_topic(message.topic)

        logging.debug("Downlink traffic: %s | %s", sink_id, request.req_id)

        sink = self.sink_manager.get_sink(sink_id)
        if sink is not None:
            if request.hop_limit > self.MAX_HOP_LIMIT:
                res = wmm.GatewayResultCode.GW_RES_INVALID_MAX_HOP_COUNT
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
            logging.warning("No sink with id: %s", sink_id)
            # No sink with  this id
            res = wmm.GatewayResultCode.GW_RES_INVALID_SINK_ID

        # Answer to backend
        response = wmm.SendDataResponse(request.req_id, self.gw_id, res, sink_id)
        topic = TopicGenerator.make_send_data_response_topic(self.gw_id, sink_id)

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    def _on_get_configs_cmd_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        logging.info("Config request received")
        try:
            request = wmm.GetConfigsRequest.from_payload(message.payload)
        except wmm.GatewayAPIParsingException as e:
            logging.error(str(e))
            return

        # Create a list of different sink configs
        configs = []
        for sink in self.sink_manager.get_sinks():
            config, _ = sink.read_config()
            if config is not None:
                configs.append(config)

        response = wmm.GetConfigsResponse(
            request.req_id, self.gw_id, wmm.GatewayResultCode.GW_RES_OK, configs
        )
        topic = TopicGenerator.make_get_configs_response_topic(self.gw_id)

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    def _on_get_gateway_info_cmd_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        """
        This function doesn't need the decorator @deferred_thread as request is handled
        without I/O
        """
        logging.info("Gateway info request received")
        try:
            request = wmm.GetGatewayInfoRequest.from_payload(message.payload)
        except wmm.GatewayAPIParsingException as e:
            logging.error(str(e))
            return

        response = wmm.GetGatewayInfoResponse(
            request.req_id,
            self.gw_id,
            wmm.GatewayResultCode.GW_RES_OK,
            current_time_s_epoch=int(time()),
            gateway_model=self.gw_model,
            gateway_version=self.gw_version,
            implemented_api_version=IMPLEMENTED_API_VERSION,
        )

        topic = TopicGenerator.make_get_gateway_info_response_topic(self.gw_id)
        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    @update_gateway_status_dec
    def _on_set_config_cmd_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        logging.info("Set config request received")
        try:
            request = wmm.SetConfigRequest.from_payload(message.payload)
        except wmm.GatewayAPIParsingException as e:
            logging.error(str(e))
            return

        logging.debug("Set sink config: %s", request)
        sink = self.sink_manager.get_sink(request.sink_id)
        if sink is not None:
            res = sink.write_config(request.new_config)
            new_config, _ = sink.read_config()
        else:
            res = wmm.GatewayResultCode.GW_RES_INVALID_SINK_ID
            new_config = None

        response = wmm.SetConfigResponse(
            request.req_id, self.gw_id, res, request.sink_id, new_config
        )
        topic = TopicGenerator.make_set_config_response_topic(
            self.gw_id, request.sink_id
        )

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    def _on_otap_status_request_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        logging.info("OTAP status request received")
        try:
            request = wmm.GetScratchpadStatusRequest.from_payload(message.payload)
        except wmm.GatewayAPIParsingException as e:
            logging.error(str(e))
            return

        sink = self.sink_manager.get_sink(request.sink_id)
        if sink is not None:
            d = sink.get_scratchpad_status()

            try:
                target_and_action = d["target_and_action"]
            except KeyError:
                target_and_action = None

            response = wmm.GetScratchpadStatusResponse(
                request.req_id,
                self.gw_id,
                wmm.GatewayResultCode.GW_RES_OK,
                request.sink_id,
                d["stored_scratchpad"],
                d["stored_status"],
                d["stored_type"],
                d["processed_scratchpad"],
                d["firmware_area_id"],
                target_and_action,
            )
        else:
            response = wmm.GetScratchpadStatusResponse(
                request.req_id,
                self.gw_id,
                wmm.GatewayResultCode.GW_RES_INVALID_SINK_ID,
                request.sink_id,
            )

        topic = TopicGenerator.make_otap_status_response_topic(
            self.gw_id, request.sink_id
        )

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    @update_gateway_status_dec
    def _on_otap_upload_scratchpad_request_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        logging.info("OTAP upload request received")
        try:
            request = wmm.UploadScratchpadRequest.from_payload(message.payload)
        except wmm.GatewayAPIParsingException as e:
            logging.error(str(e))
            return

        logging.info("OTAP upload request received for %s", request.sink_id)

        sink = self.sink_manager.get_sink(request.sink_id)
        if sink is not None:
            res = sink.upload_scratchpad(request.seq, request.scratchpad)
        else:
            res = wmm.GatewayResultCode.GW_RES_INVALID_SINK_ID

        response = wmm.UploadScratchpadResponse(
            request.req_id, self.gw_id, res, request.sink_id
        )

        topic = TopicGenerator.make_otap_upload_scratchpad_response_topic(
            self.gw_id, request.sink_id
        )

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    def _on_otap_process_scratchpad_request_received(self, client, userdata, message):
        # pylint: disable=unused-argument
        logging.info("OTAP process request received")
        try:
            request = wmm.ProcessScratchpadRequest.from_payload(message.payload)
        except wmm.GatewayAPIParsingException as e:
            logging.error(str(e))
            return

        sink = self.sink_manager.get_sink(request.sink_id)
        if sink is not None:
            res = sink.process_scratchpad()
        else:
            res = wmm.GatewayResultCode.GW_RES_INVALID_SINK_ID

        response = wmm.ProcessScratchpadResponse(
            request.req_id, self.gw_id, res, request.sink_id
        )

        topic = TopicGenerator.make_otap_process_scratchpad_response_topic(
            self.gw_id, request.sink_id
        )

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    @deferred_thread
    @update_gateway_status_dec
    def _on_otap_set_target_scratchpad_request_received(
        self, client, userdata, message
    ):
        # pylint: disable=unused-argument
        res = wmm.GatewayResultCode.GW_RES_OK
        logging.info("OTAP set target request received")
        try:
            request = wmm.SetScratchpadTargetAndActionRequest.from_payload(
                message.payload
            )
            action = request.target["action"]
        except wmm.GatewayAPIParsingException as e:
            logging.error(str(e))
            return
        except KeyError:
            logging.error("Action is mandatory")
            res = wmm.GatewayResultCode.GW_RES_INVALID_PARAM

        if res == wmm.GatewayResultCode.GW_RES_OK:
            # Get optional params (None if not present)
            seq = request.target.get("target_sequence")
            crc = request.target.get("target_crc")
            delay = request.target.get("delay")
            if delay is not None:
                # Convert predefined delay to right format
                if delay is wmm.ProcessingDelay.DELAY_TEN_MINUTES:
                    param = 0x4A
                elif delay is wmm.ProcessingDelay.DELAY_THIRTY_MINUTES:
                    param = 0x5E
                elif delay is wmm.ProcessingDelay.DELAY_ONE_HOUR:
                    param = 0x81
                elif delay is wmm.ProcessingDelay.DELAY_SIX_HOURS:
                    param = 0x86
                elif delay is wmm.ProcessingDelay.DELAY_ONE_DAY:
                    param = 0xC1
                elif delay is wmm.ProcessingDelay.DELAY_TWO_DAYS:
                    param = 0xC2
                elif delay is wmm.ProcessingDelay.DELAY_FIVE_DAYS:
                    param = 0xC5
                else:
                    # Unknown value, set to 0, will generate an error later
                    param = 0
            else:
                param = request.target.get("param")

            # no error so far
            sink = self.sink_manager.get_sink(request.sink_id)
            if sink is not None:
                res = sink.set_target_scratchpad(
                    action=action, target_seq=seq, target_crc=crc, param=param
                )
            else:
                res = wmm.GatewayResultCode.GW_RES_INVALID_SINK_ID

        response = wmm.SetScratchpadTargetAndActionResponse(
            request.req_id, self.gw_id, res, request.sink_id
        )

        topic = TopicGenerator.make_otap_set_target_scratchpad_response_topic(
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

    _check_duplicate(settings, "host", "mqtt_hostname", None)
    _check_duplicate(settings, "port", "mqtt_port", 8883)
    _check_duplicate(settings, "username", "mqtt_username", None)
    _check_duplicate(settings, "password", "mqtt_password", None)
    _check_duplicate(settings, "tlsfile", "mqtt_certfile", None)
    _check_duplicate(
        settings, "unsecure_authentication", "mqtt_force_unsecure", False
    )
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
    if settings.mqtt_force_unsecure and settings.mqtt_certfile:
        # If tls cert file is provided, unsecure authentication cannot
        # be set
        logging.error("Cannot give certfile and disable secure authentication")
        exit()

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
    parse.add_buffering_settings()
    parse.add_debug_settings()
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

    debug_level = "{0}".format(debug_level.upper())

    # enable its logger
    logging.basicConfig(
        format=f'%(asctime)s | [%(levelname)s] {__pkg_name__}@%(filename)s:%(lineno)d:%(message)s',
        level=debug_level,
        stream=sys.stdout
    )

    _update_parameters(settings)
    # after this stage, mqtt deprecated argument cannot be used

    _check_parameters(settings)

    TransportService(settings=settings).run()


if __name__ == "__main__":
    main()
