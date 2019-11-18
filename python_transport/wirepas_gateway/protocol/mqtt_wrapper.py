# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import queue
import socket
import ssl
from select import select
from threading import Thread, current_thread
from time import sleep

from paho.mqtt import client as mqtt
from paho.mqtt.client import connack_string


class MQTTWrapper(Thread):
    """
    Class to manage the MQTT main thread and be able to share it with other services
    In this case, it allows to have all the related mqtt activity happening on same thread
    to avoid any dead lock from mqtt client.
    """

    # Keep alive time with broker
    KEEP_ALIVE_S = 60

    # Reconnect timeout in Seconds
    TIMEOUT_RECONNECT_S = 120

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

        self._client = mqtt.Client(
            client_id=settings.gateway_id,
            clean_session=not settings.mqtt_persist_session,
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

        self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self._client.on_connect = self._on_connect

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

        # Set options to initial socket
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
                    self._client.publish(topic, payload, qos=qos, retain=retain)

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

        # Socket is not opened anymore, try to reconnect
        timeout = MQTTWrapper.TIMEOUT_RECONNECT_S
        while timeout > 0:
            try:
                ret = self._client.reconnect()
                if ret == mqtt.MQTT_ERR_SUCCESS:
                    break
            except Exception:
                # Retry to connect in 1 sec up to timeout
                sleep(1)
                timeout -= 1
                self.logger.debug("Retrying to connect in 1 sec")

        if timeout <= 0:
            self.logger.error(
                "Unable to reconnect after %s seconds", MQTTWrapper.TIMEOUT_RECONNECT_S
            )
            return None

        # Socket must be available once reconnect is successful
        if self._client.socket() is None:
            self.logger.error("Cannot get socket after reconnect")
            return None

        # Set options to new reopened socket
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

    def publish(self, topic, payload, qos=1, retain=False) -> None:
        """
        Method to publish to Mqtt from a different thread.
        :param topic: Topic to publish on
        :param payload: Payload
        :param qos: Qos to use
        :param retain: Is it a retain message
        """
        if current_thread().ident == self.ident:
            # Already on right thread
            self._client.publish(topic, payload, qos, retain)
        else:
            # Send it to the queue to be published from Mqtt thread
            self._publish_queue.put((topic, payload, qos, retain))

    def subscribe(self, topic, cb, qos=2) -> None:
        self.logger.debug("Subscribing to: {}".format(topic))
        self._client.subscribe(topic, qos)
        self._client.message_callback_add(topic, cb)


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

    def put(self, item, block=True, timeout=None):
        # Insert item in queue
        super().put(item, block, timeout)
        # Send 1 byte on socket to signal select
        self._putsocket.send(b"x")

    def get(self, block=False, timeout=None):
        # Get item first so get can be called and
        # raise empty exception without blocking in recv
        item = super().get(block, timeout)
        # Consume 1 byte from socket for each item
        self._getsocket.recv(1)
        return item
