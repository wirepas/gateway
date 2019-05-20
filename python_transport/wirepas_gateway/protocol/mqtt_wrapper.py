# Wirepas Oy licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import queue
import socket
import ssl
from select import select
from threading import Thread, current_thread
from time import sleep

from paho.mqtt import client as mqtt


class MQTTWrapper(Thread):
    """
    Class to manage the MQTT main thread and be able to share it with other services
    In this case, it allows to have all the related mqtt activity happening on same thread
    to avoid any dead lock from mqtt client.
    """

    def __init__(self, logger, username, password, host, port, secure_auth=True, tlsfile=None,
                 on_termination_cb=None, on_connect_cb=None):
        Thread.__init__(self)
        self.daemon = True
        self.running = False
        self.logger = logger
        self.on_termination_cb = on_termination_cb
        self.on_connect_cb = on_connect_cb

        self._client = mqtt.Client()
        if secure_auth:
            try:
                self._client.tls_set(
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

        self._client.username_pw_set(username, password)
        self._client.on_connect = self._on_connect

        try:
            self._client.connect(host, port, keepalive=60)
        except (socket.gaierror, ValueError) as e:
            self.logger.error("Cannot connect to mqtt {}".format(e))
            exit(-1)

        # Set options to initial socket
        self._client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

        self._publish_queue = SelectableQueue()

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            self.logger.error("MQTT cannot connect {}".format(rc))
            return

        if self.on_connect_cb is not None:
            self.on_connect_cb()

    def _do_select(self, sock):
        # Select with a timeout of 1 sec to call loop misc from time to time
        r, w, e = select(
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
                    try:
                        self._client._sockpairR.recv(1)
                    except Exception:
                        # This socket is not used at all, so if something is wrong,
                        # not a big issue. Just keep going
                        pass

            except TimeoutError:
                self.logger.debug("Timeout to send payload: {}".format(payload))
                # In theory, mqtt client shouldn't loose the last packet
                # If it is not the case, following line could be uncommented
                # self._publish_queue.put((topic, payload, qos, retain))
                raise
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

        # Socket is not opened anymore, try to reconnect
        while True:
            try:
                self._client.reconnect()
                break
            except Exception:
                # Retry to connect in 1 sec
                sleep(1)

        # Wait for socket to reopen
        # Do it in polling as we are managing the thread ourself
        # so no callback possible
        while self._client.socket() is None:
            sleep(1)

        # Set options to new reopened socket
        self._client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
        return self._client.socket()

    def set_last_will(self, topic, data):
        # Set Last wil message
        self._client.will_set(topic, data, qos=2, retain=True)

    def run(self):
        while True:
            try:
                # Get client socket to select on it
                # This function manage the reconnect
                sock = self._get_socket()

                self._do_select(sock)
            except TimeoutError:
                self.logger.error("Timeout in connection, force a reconnect")
                self._client.reconnect()
            except Exception:
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
