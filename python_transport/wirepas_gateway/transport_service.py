# Wirepas Oy licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import paho.mqtt.client as mqtt
import ssl
import os
import socket
import queue

from select import select
from socket import timeout
from threading import Thread, current_thread
from time import sleep, time
from uuid import getnode

from wirepas_gateway.dbus.dbus_client import BusClient
from wirepas_gateway.protocol.topic_helper import TopicGenerator, TopicParser

import wirepas_messaging
from wirepas_messaging.gateway.api import (
    GatewayResultCode,
    GatewayState,
    GatewayAPIParsingException,
)

from wirepas_gateway.utils import setup_log
from wirepas_gateway.utils import ParserHelper

# This constant is the actual API level implemented by this transport module (cf WP-RM-128)
IMPLEMENTED_API_VERSION = 1


class SelectableQueue(queue.Queue):
    """
    Wrapper arround a Queue to make it selectable with an associated
    socket
    """

    def __init__(self):
        super().__init__()
        self._putsocket, self._getsocket = socket.socketpair()

    def fileno(self):
        """
        Implement fileno to be selectable
        :return: the reception socket fileno
        """
        return self._getsocket.fileno()

    def put(self, item):
        # Insert item in queue
        super().put(item)
        # Send 1 byte on socket to signal select
        self._putsocket.send(b"x")

    def get(self):
        # Get item first so get can be called and
        # raise empty exception without blocking in recv
        item = super().get(block=False)
        # Consume 1 byte from socket for each item
        self._getsocket.recv(1)
        return item


class MQTTWrapper(Thread):
    """
    Class to manage the MQTT main thread and be able to share it with other services
    In this case, it allows to have all the related mqtt activity happening on same thread
    to avoid any dead lock from mqtt client.
    """

    def __init__(self, client, logger, on_termination_cb=None):
        Thread.__init__(self)
        self.daemon = True
        self.running = False
        self.client = client
        self.logger = logger
        self.on_termination_cb = on_termination_cb

        # Set options to initial socket
        self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

        self._publish_queue = SelectableQueue()

    def _do_select(self, sock):
        # Select with a timeout of 1 sec to call loop misc from time to time
        r, w, e = select(
            [sock, self._publish_queue],
            [sock] if self.client.want_write() else [],
            [],
            1,
        )

        # Check if we have something to publish
        if self._publish_queue in r:
            try:
                # Publish everything. Loop is not necessary as
                # next select will exit immediately if queue not empty
                while True:
                    topic, payload, qos, retain = self._publish_queue.get()
                    self.client.publish(topic, payload, qos=qos, retain=retain)
            except timeout as e:
                self.logger.debug("Timeout to send payload: {}".format(payload))
                # In theory, mqtt client shouldn't loose the last packet
                # If it is not the case, following line could be uncommented
                # self._publish_queue.put((topic, payload, qos, retain))
                raise e
            except queue.Empty:
                # No more packet to publish
                pass

        if sock in r:
            self.client.loop_read()

        if sock in w:
            self.client.loop_write()

        self.client.loop_misc()

    def _get_socket(self):
        sock = self.client.socket()
        if sock is not None:
            return sock

        self.logger.error("MQTT, unexpected disconnection")

        # Socket is not opened anymore, try to reconnect
        while True:
            try:
                self.client.reconnect()
                break
            except Exception as e:
                # Retry to connect in 1 sec
                sleep(1)

        # Wait for socket to reopen
        # Do it in polling as we are managing the thread ourself
        # so no callback possible
        while self.client.socket() is None:
            sleep(1)

        # Set options to new reopened socket
        self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
        return self.client.socket()

    def run(self):
        while True:
            try:
                # Get client socket to select on it
                # This function manage the reconnect
                sock = self._get_socket()

                self._do_select(sock)
            except timeout:
                self.logger.error("Timeout in connection, force a reconnect")
                self.client.reconnect()
            except Exception as e:
                # If an exception is not catched before this point
                # All the transport module must be stopped in order to be fully
                # restarted by the managing agent
                self.logger.exception("Unexpected exception in MQTT wrapper Thread")
                if self.on_termination_cb is not None:
                    # As this thread is daemonized, inform the parent that this
                    # thread has exited
                    self.on_termination_cb()

    def publish(self, topic, payload, qos=1, retain=False) -> None:
        """
        Method to publish to Mqtt form a different thread.
        :param topic: Topic to publish on
        :param payload: Payload
        :param qos: Qos to use
        :param retain: Is it a retain message
        """
        if current_thread().ident == self.ident:
            # Already on right thread
            self.client.publish(topic, payload, qos, retain)
        else:
            # Send it to the queue to be published from Mqtt thread
            self._publish_queue.put((topic, payload, qos, retain))


class TransportService(BusClient):
    """
    Implementation of gateway to backend protocol

    Get all the events from DBUS and publih it with right format
    for gateways
    """

    # Maximum hop limit to send a packet is limited to 15 by API (4 bits)
    MAX_HOP_LIMIT = 15

    def __init__(
        self,
        host,
        port,
        username="",
        password=None,
        tlsfile=None,
        gw_id=None,
        logger=None,
        c_extension=False,
        secure_auth=False,
        gw_model=None,
        gw_version=None,
        ignored_endpoints_filter=None,
        whitened_endpoints_filter=None,
        **kwargs
    ):

        super(TransportService, self).__init__(
            logger=logger,
            c_extension=c_extension,
            ignored_ep_filter=ignored_endpoints_filter,
            **kwargs
        )

        if gw_id is None:
            self.gw_id = getnode()
        else:
            self.gw_id = gw_id

        self.gw_model = gw_model
        self.gw_version = gw_version

        self.whitened_ep_filter = whitened_endpoints_filter

        self.mqtt_client = mqtt.Client()
        if secure_auth:
            try:
                self.mqtt_client.tls_set(
                    tlsfile,
                    certfile=None,
                    keyfile=None,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLSv1_2,
                    ciphers=None,
                )
            except:
                self.logger.error(
                    "Cannot use secure authentication. attempting unsecure connection"
                )

        self.mqtt_client.username_pw_set(username, password)
        self.mqtt_client.on_connect = self._on_connect
        self._set_last_will()
        try:
            self.mqtt_client.connect(host, port, keepalive=60)
        except (socket.gaierror, ValueError) as e:
            self.logger.error("Cannot connect to mqtt {}".format(e))
            exit(-1)

        self.mqtt_wrapper = MQTTWrapper(
            self.mqtt_client, self.logger, self._on_mqtt_wrapper_termination_cb
        )
        self.mqtt_wrapper.start()

        self.logger = logger or logging.getLogger(__name__)

        self.logger.info("Gateway started with id: {}".format(self.gw_id))

    def _on_mqtt_wrapper_termination_cb(self):
        """
        Callback used to be informed when the MQTT wrapper has exited
        It is not a normal situation and better to exit the program
        to have a change to restart from a clean session
        """
        self.logger.error("MQTT wrapper ends. Terminate the program")
        self.stop_dbus_client()

    def _set_last_will(self):
        event = wirepas_messaging.gateway.api.StatusEvent(
            self.gw_id, GatewayState.OFFLINE
        )

        topic = TopicGenerator.make_status_topic(self.gw_id)

        # Set Last wil message
        self.mqtt_client.will_set(topic, event.payload, qos=2, retain=True)

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            self.logger.error("MQTT cannot connect {}".format(rc))
            return

        # Register for get gateway info
        topic = TopicGenerator.make_get_gateway_info_request_topic(self.gw_id)
        self.logger.debug("Subscribing to: {}".format(topic))
        self.mqtt_client.subscribe(topic, qos=2)
        self.mqtt_client.message_callback_add(
            topic, self._on_get_gateway_info_cmd_received
        )

        # Register for get configs request
        topic = TopicGenerator.make_get_configs_request_topic(self.gw_id)
        self.logger.debug("Subscribing to: {}".format(topic))
        # If duplicated request, it doesn't harm so QOS could be 1
        self.mqtt_client.subscribe(topic, qos=2)
        self.mqtt_client.message_callback_add(topic, self._on_get_configs_cmd_received)

        # Register for set config request for any sink
        topic = TopicGenerator.make_set_config_request_topic(self.gw_id)
        self.logger.debug("Subscribing to: {}".format(topic))
        # Receiving multiple time the same config is not an issue but better to
        # have qos 2
        self.mqtt_client.subscribe(topic, qos=2)
        self.mqtt_client.message_callback_add(topic, self._on_set_config_cmd_received)

        # Register for send data request for any sink on the gateway
        topic = TopicGenerator.make_send_data_request_topic(self.gw_id)
        self.logger.debug("Subscribing to: {}".format(topic))
        # It is important to have a qos of 2 and also from the publisher as 1 could generate
        # duplicated packets and we don't know the consequences on end
        # application
        self.mqtt_client.subscribe(topic, qos=2)
        self.mqtt_client.message_callback_add(topic, self._on_send_data_cmd_received)

        # Register for otap commands for any sink on the gateway
        topic = TopicGenerator.make_otap_status_request_topic(self.gw_id)
        self.logger.debug("Subscribing to: {}".format(topic))
        self.mqtt_client.subscribe(topic, qos=2)
        self.mqtt_client.message_callback_add(
            topic, self._on_otap_status_request_received
        )

        topic = TopicGenerator.make_otap_load_scratchpad_request_topic(self.gw_id)
        self.logger.debug("Subscribing to: {}".format(topic))
        self.mqtt_client.subscribe(topic, qos=2)
        self.mqtt_client.message_callback_add(
            topic, self._on_otap_upload_scratchpad_request_received
        )

        topic = TopicGenerator.make_otap_process_scratchpad_request_topic(self.gw_id)
        self.logger.debug("Subscribing to: {}".format(topic))
        self.mqtt_client.subscribe(topic, qos=2)
        self.mqtt_client.message_callback_add(
            topic, self._on_otap_process_scratchpad_request_received
        )

        event = wirepas_messaging.gateway.api.StatusEvent(
            self.gw_id, GatewayState.ONLINE
        )

        topic = TopicGenerator.make_status_topic(self.gw_id)
        self.logger.debug("Subscribing to: {}".format(topic))
        self.mqtt_client.publish(topic, event.payload, qos=1, retain=True)

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
                "Message received from unknown sink at the moment {}".format(sink_id)
            )
            return None

        network_address = sink.get_network_address()

        topic = TopicGenerator.make_received_data_topic(
            self.gw_id, sink_id, network_address, src_ep, dst_ep
        )
        self.logger.debug("Sending data to: {}".format(topic))
        # Set qos to 1 to avoid loading too much the broker
        # unique id in event header can be used for duplicate filtering in
        # backends
        self.mqtt_wrapper.publish(topic, event.payload, qos=1)

    def on_stack_started(self, name):
        sink = self.sink_manager.get_sink(name)
        if sink is None:
            self.logger.error("Sink started {} error: unknown sink".format(name))
            return None

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

    def on_sink_connected(self, name):
        self.logger.info("Sink connected, sending new configs")
        self._send_asynchronous_get_configs_response()

    def on_sink_disconnected(self, name):
        self.logger.info("Sink disconnected, sending new configs")
        self._send_asynchronous_get_configs_response()

    def _on_send_data_cmd_received(self, client, userdata, message):
        self.logger.info("Request to send data")
        try:
            request = wirepas_messaging.gateway.api.SendDataRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return None

        # Get the sink-id from topic
        gw_id, sink_id = TopicParser.parse_send_data_topic(message.topic)

        self.logger.debug("Request for sink {} ".format(sink_id))

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
            self.logger.warning("No sink with id: {}".format(sink_id))
            # No sink with  this id
            res = GatewayResultCode.GW_RES_INVALID_SINK_ID

        # Answer to backend
        response = wirepas_messaging.gateway.api.SendDataResponse(
            request.req_id, self.gw_id, res, sink_id
        )
        topic = TopicGenerator.make_send_data_response_topic(self.gw_id, sink_id)

        self.mqtt_wrapper.publish(topic, response.payload, qos=2)

    def _on_get_configs_cmd_received(self, client, userdata, message):
        self.logger.info("Config request received")
        try:
            request = wirepas_messaging.gateway.api.GetConfigsRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return None

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
        self.logger.info("Gateway info request received")
        try:
            request = wirepas_messaging.gateway.api.GetGatewayInfoRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return None

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

    def _on_set_config_cmd_received(self, client, userdata, message):
        self.logger.info("Set config request received")
        try:
            request = wirepas_messaging.gateway.api.SetConfigRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return None

        self.logger.debug("Set sink config: {}".format(request))
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

    def _on_otap_status_request_received(self, client, userdata, message):
        self.logger.info("OTAP status request received")
        try:
            request = wirepas_messaging.gateway.api.GetScratchpadStatusRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return None

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

    def _on_otap_upload_scratchpad_request_received(self, client, userdata, message):
        self.logger.info("OTAP upload request received")
        try:
            request = wirepas_messaging.gateway.api.UploadScratchpadRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return None

        self.logger.info("OTAP upload request received for {}".format(request.sink_id))

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

    def _on_otap_process_scratchpad_request_received(self, client, userdata, message):
        self.logger.info("OTAP process request received")
        try:
            request = wirepas_messaging.gateway.api.ProcessScratchpadRequest.from_payload(
                message.payload
            )
        except GatewayAPIParsingException as e:
            self.logger.error(str(e))
            return None

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
        except ValueError as e:
            # Probably a range
            pass

        # Check if ep is a range
        try:
            lower, upper = ep.split("-")
            lower = int(lower)
            upper = int(upper)
            if lower > upper or lower < 0 or upper > 255:
                raise SyntaxError("Wrong EP range value")

            single_list += list(range(lower, upper + 1))
        except (AttributeError, ValueError):
            raise SyntaxError("Wrong EP range format")

    return single_list


def main():
    """
        Main service for transport module

    """
    ParserHelper()
    parse = ParserHelper(description="Default arguments")

    parse.add_transport()
    parse.add_file_settings()

    args = parse.settings(skip_undefined=False)

    try:
        debug_level = os.environ["DEBUG_LEVEL"]
    except KeyError:
        debug_level = "debug"

    logger = setup_log("transport_service", level=debug_level)

    if args.unsecure_authentication and args.tlsfile:
        # If tls cert file is provided, unsecure authentication cannot
        # be set
        logger.error("Cannot set tls file and disable secure authentication")
        exit()

    secure_authentication = not args.unsecure_authentication

    if args.full_python:
        logger.info("Starting transport without C optimisation")
        c_extension = False
    else:
        c_extension = True

    # Parse EP list that should not be published
    ignored_endpoints_filter = None
    if args.ignored_endpoints_filter is not None:
        try:
            ignored_endpoints_filter = parse_setting_list(args.ignored_endpoints_filter)
            logger.debug("Ignored endpoints are: {}".format(ignored_endpoints_filter))
        except SyntaxError as e:
            logger.error(
                "Wrong format for ignored_endpoints_filter EP list ({})".format(e)
            )
            exit()

    # Parse EP list that should be published without payload
    whitened_endpoints_filter = None
    if args.whitened_endpoints_filter is not None:
        try:
            whitened_endpoints_filter = parse_setting_list(
                args.whitened_endpoints_filter
            )
            logger.debug("Whitened endpoints are: {}".format(whitened_endpoints_filter))
        except SyntaxError as e:
            logger.error(
                "Wrong format for whitened_endpoints_filter EP list ({})".format(e)
            )
            exit()

    try:
        if set(ignored_endpoints_filter) & set(whitened_endpoints_filter):
            logger.warning("Some endpoints are both ignored and whitened")
    except TypeError:
        # One of the filter list is None
        pass

    TransportService(
        args.host,
        args.port,
        args.username,
        args.password,
        args.tlsfile,
        args.gwid,
        logger,
        c_extension,
        secure_authentication,
        args.gateway_model,
        args.gateway_version,
        ignored_endpoints_filter,
        whitened_endpoints_filter,
    ).run()


if __name__ == "__main__":
    """ executes main. """
    main()
