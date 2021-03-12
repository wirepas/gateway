# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import queue
import socket
import ssl
from select import select
from threading import Thread, Lock
from time import sleep
from datetime import datetime

from paho.mqtt import client as mqtt
from paho.mqtt.client import connack_string


class MQTTWrapper(Thread):
    """
    Class to manage the MQTT main thread and be able to share it with other services
    In this case, it allows to have all the related mqtt activity happening on same thread
    to avoid any dead lock from mqtt client.
    """

    # Keep alive time with broker
    KEEP_ALIVE_S = 20

    def __init__(
        self,
        settings,
        logger,
        on_termination_cb=None,
        on_connect_cb=None,
        last_will_topic=None,
        last_will_data=None,
    ):
        Thread.__init__(self)
        self.daemon = True
        self.running = False
        self.logger = logger
        self.on_termination_cb = on_termination_cb
        self.on_connect_cb = on_connect_cb
        # Set to track the unpublished packets
        self._unpublished_mid_set = set()
        # Variable to keep track of latest published packet
        self._timestamp_last_publish = datetime.now()

        if settings.mqtt_use_websocket:
            transport = "websockets"
            self._use_websockets = True
        else:
            transport = "tcp"
            self._use_websockets = False

        self._client = mqtt.Client(
            client_id=settings.gateway_id,
            clean_session=not settings.mqtt_persist_session,
            transport=transport,
        )

        if not settings.mqtt_force_unsecure:
            try:
                self._client.tls_set(
                    ca_certs=settings.mqtt_ca_certs,
                    certfile=settings.mqtt_certfile,
                    keyfile=settings.mqtt_keyfile,
                    cert_reqs=ssl.VerifyMode[settings.mqtt_cert_reqs],
                    tls_version=ssl._SSLMethod[settings.mqtt_tls_version],
                    ciphers=settings.mqtt_ciphers,
                )
            except Exception as e:
                self.logger.error("Cannot use secure authentication %s", e)
                exit(-1)

        self.logger.info(
            "Max inflight messages set to %s", settings.mqtt_max_inflight_messages
        )
        self._client.max_inflight_messages_set(settings.mqtt_max_inflight_messages)

        self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self._client.on_connect = self._on_connect
        self._client.on_publish = self._on_publish

        if last_will_topic is not None and last_will_data is not None:
            self._set_last_will(last_will_topic, last_will_data)

        try:
            self._client.connect(
                settings.mqtt_hostname,
                settings.mqtt_port,
                keepalive=MQTTWrapper.KEEP_ALIVE_S,
            )
        except (socket.gaierror, ValueError) as e:
            self.logger.error("Cannot connect to mqtt %s", e)
            exit(-1)

        self.timeout = settings.mqtt_reconnect_delay

        # Set options to initial socket if tcp transport only
        if not self._use_websockets:
            self._client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

        self._publish_queue = SelectableQueue()

        # Thread is not started yes
        self.running = False
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        # pylint: disable=unused-argument
        if rc != 0:
            self.logger.error("MQTT cannot connect: %s (%s)", connack_string(rc), rc)
            self.running = False
            return

        self.connected = True
        if self.on_connect_cb is not None:
            self.on_connect_cb()

    def _on_publish(self, client, userdata, mid):
        self._unpublished_mid_set.remove(mid)
        self._timestamp_last_publish = datetime.now()
        return

    def _do_select(self, sock):
        # Select with a timeout of 1 sec to call loop misc from time to time
        r, w, _ = select(
            [sock, self._publish_queue],
            [sock] if self._client.want_write() else [],
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

                    self._publish_from_wrapper_thread(
                        topic, payload, qos=qos, retain=retain
                    )

                    # FIX: read internal sockpairR as it is written but
                    # never read as we don't use the internal paho loop
                    # but we have spurious timeout / broken pipe from
                    # this socket pair
                    # pylint: disable=protected-access
                    try:
                        self._client._sockpairR.recv(1)
                    except Exception:
                        # This socket is not used at all, so if something is wrong,
                        # not a big issue. Just keep going
                        pass

            except queue.Empty:
                # No more packet to publish
                pass

        if sock in r:
            self._client.loop_read()

        if sock in w:
            self._client.loop_write()

        self._client.loop_misc()

    def _get_socket(self):
        sock = self._client.socket()
        if sock is not None:
            return sock

        self.logger.error("MQTT, unexpected disconnection")

        if not self.connected:
            self.logger.error("Impossible to connect - authentication failure ?")
            return None

        # Socket is not opened anymore, try to reconnect for timeout if set
        loop_forever = self.timeout == 0
        delay = 0

        # Loop forever or until timeout is over
        while loop_forever or (delay <= self.timeout):
            try:
                ret = self._client.reconnect()
                if ret == mqtt.MQTT_ERR_SUCCESS:
                    break
            except Exception:
                # Retry to connect in 1 sec up to timeout if set
                sleep(1)
                delay += 1
                self.logger.debug("Retrying to connect in 1 sec")

        if not loop_forever:
            # In case of timeout set, check if it exits because of timeout
            if delay > self.timeout:
                self.logger.error("Unable to reconnect after %s seconds", delay)
                return None

        # Socket must be available once reconnect is successful
        if self._client.socket() is None:
            self.logger.error("Cannot get socket after reconnect")
            return None

        # Set options to new reopened socket
        if not self._use_websockets:
            self._client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
        return self._client.socket()

    def _set_last_will(self, topic, data):
        # Set Last wil message
        self._client.will_set(topic, data, qos=2, retain=True)

    def run(self):
        self.running = True
        while self.running:
            try:
                # Get client socket to select on it
                # This function manage the reconnect
                sock = self._get_socket()
                if sock is None:
                    # Cannot get the socket, probably an issue
                    # with connection. Exit the thread
                    self.logger.error("Cannot get MQTT socket, exit...")
                    self.running = False
                else:
                    self._do_select(sock)
            except TimeoutError:
                self.logger.error("Timeout in connection, force a reconnect")
                self._client.reconnect()
            except Exception:
                # If an exception is not catched before this point
                # All the transport module must be stopped in order to be fully
                # restarted by the managing agent
                self.logger.exception("Unexpected exception in MQTT wrapper Thread")
                self.running = False

        if self.on_termination_cb is not None:
            # As this thread is daemonized, inform the parent that this
            # thread has exited
            self.on_termination_cb()

    def _publish_from_wrapper_thread(self, topic, payload, qos, retain):
        """Internal method to publish on Mqtt. This method is only called from
        mqtt wrapper thread to avoid races.

        Args:
            topic: Topic to publish on
            payload: Payload
            qos: Qos to use
            retain: Is it a retain message

        """
        mid = self._client.publish(topic, payload, qos=qos, retain=retain).mid
        if self.publish_queue_size == 0:
            # Reset last published packet
            self._timestamp_last_publish = datetime.now()
        self._unpublished_mid_set.add(mid)

    def publish(self, topic, payload, qos=1, retain=False) -> None:
        """ Method to publish to Mqtt from any thread

        Args:
            topic: Topic to publish on
            payload: Payload
            qos: Qos to use
            retain: Is it a retain message

        """
        # Send it to the queue to be published from Mqtt thread
        self._publish_queue.put((topic, payload, qos, retain))

    def subscribe(self, topic, cb, qos=2) -> None:
        self.logger.debug("Subscribing to: {}".format(topic))
        self._client.subscribe(topic, qos)
        self._client.message_callback_add(topic, cb)

    @property
    def publish_queue_size(self):
        return len(self._unpublished_mid_set) + self._publish_queue.get_size()

    @property
    def last_published_packet_s(self):
        delta = datetime.now() - self._timestamp_last_publish
        return delta.total_seconds()


class SelectableQueue(queue.Queue):
    """
    Wrapper arround a Queue to make it selectable with an associated
    socket
    """

    def __init__(self):
        super().__init__()
        self._putsocket, self._getsocket = socket.socketpair()
        self._lock = Lock()
        self._size = 0

    def fileno(self):
        """
        Implement fileno to be selectable
        :return: the reception socket fileno
        """
        return self._getsocket.fileno()

    def get_size(self):
        with self._lock:
            return self._size

    def put(self, item, block=True, timeout=None):
        with self._lock:
            if self._size == 0:
                # Send 1 byte on socket to signal select
                self._putsocket.send(b"x")
            self._size = self._size + 1

            # Insert item in queue
            super().put(item, block, timeout)

    def get(self, block=False, timeout=None):
        with self._lock:
            # Get item first so get can be called and
            # raise empty exception
            item = super().get(block, timeout)

            self._size = self._size - 1
            if self._size == 0:
                # Consume 1 byte from socket
                self._getsocket.recv(1)
            return item
