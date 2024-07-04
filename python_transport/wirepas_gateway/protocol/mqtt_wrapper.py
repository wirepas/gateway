# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import logging
import queue
import socket
import ssl
from select import select
from threading import Thread, Lock
from time import sleep, monotonic
from datetime import datetime
from random import randrange

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
        on_termination_cb=None,
        on_connect_cb=None,
        last_will_topic=None,
        last_will_data=None,
    ):
        Thread.__init__(self)
        self.daemon = True
        self.running = False
        self.on_termination_cb = on_termination_cb
        self.on_connect_cb = on_connect_cb
        # Set to track the unpublished packets
        self._unpublished_mid_set = set()
        # Keep track of latest published packet
        self._publish_monitor = PublishMonitor()

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
                logging.error("Cannot use secure authentication %s", e)
                exit(-1)

        logging.info(
            "Max inflight messages set to %s", settings.mqtt_max_inflight_messages
        )
        self._client.max_inflight_messages_set(settings.mqtt_max_inflight_messages)
        self._max_inflight_messages = settings.mqtt_max_inflight_messages

        self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self._client.on_connect = self._on_connect
        self._client.on_publish = self._on_publish
        self._client.on_disconnect = self._on_disconnect

        if last_will_topic is not None and last_will_data is not None:
            self._set_last_will(last_will_topic, last_will_data)

        try:
            self._client.connect(
                settings.mqtt_hostname,
                settings.mqtt_port,
                keepalive=MQTTWrapper.KEEP_ALIVE_S,
            )
        except (socket.gaierror, ValueError) as e:
            logging.error(
                "Error on MQTT address %s:%d => %s"
                % (settings.mqtt_hostname, settings.mqtt_port, str(e))
            )
            # Do not exit as it and let the retry mechanism
            # to reconnect. It can happen if connection is not available yet.
            # mqtt_reconnect_delay setting can be used to limit the retry.
        except ConnectionRefusedError:
            logging.error("Connection Refused by MQTT broker")
            exit(-1)
        except OSError as e:
            logging.error("Cannot establish connection (%s)", str(e))
            # It will happen if broker is down when trying first connection.
            # But it can happen also if settings are wrong (host or port)
            # mqtt_reconnect_delay setting can be used to limit the retry.

        self.timeout = settings.mqtt_reconnect_delay

        # Set options to initial socket if tcp transport only
        if not self._use_websockets and self._client.socket() is not None:
            self._client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

        self._publish_queue = SelectableQueue(rate_limit_pps=settings.mqtt_rate_limit_pps)
        if settings.mqtt_rate_limit_pps >= 0:
            logging.info("Rate control set to %s", settings.mqtt_rate_limit_pps)

        # Thread is not started yes
        self.running = False
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        # pylint: disable=unused-argument
        if rc != 0:
            logging.error("MQTT cannot connect: %s (%s)", connack_string(rc), rc)
            self.running = False
            return

        self.connected = True
        if self.on_connect_cb is not None:
            self.on_connect_cb()

    def _on_disconnect(self, userdata, rc):
        if rc != 0:
            logging.error(
                "MQTT unexpected disconnection (network or broker originated):"
                "%s (%s)",
                connack_string(rc),
                rc,
            )
            self.connected = False

    def _on_publish(self, client, userdata, mid):
        self._unpublished_mid_set.remove(mid)
        self._publish_monitor.on_publish_done()
        return

    def _do_select(self, sock):
        # Select with a timeout of 1 sec to call loop misc from time to time
        r, w, _ = select(
            [sock, self._publish_queue],
            [sock] if self._client.want_write() else [],
            [],
            1,
        )

        if sock in r:
            self._client.loop_read()

        if sock in w:
            self._client.loop_write()

        self._client.loop_misc()
        # Check if we have something to publish
        if self._publish_queue in r:
            try:
                while len(self._unpublished_mid_set) < self._max_inflight_messages:
                    # Publish a single packet from our queue
                    topic, payload, qos, retain = self._publish_queue.get()
                    info = self._client.publish(topic, payload, qos=qos, retain=retain)
                    self._unpublished_mid_set.add(info.mid)

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

    def _get_socket(self):
        sock = self._client.socket()
        if sock is not None:
            return sock

        if self.connected:
            logging.error("MQTT Inner loop, unexpected disconnection")

        start_disconnection = monotonic()
        # Socket is not opened anymore, try to reconnect for timeout if set
        if self.timeout == 0:
            loop_forever = True
        else:
            loop_forever = False
            loop_until = monotonic() + self.timeout

        logging.info("Starting reconnect loop with timeout %d" % self.timeout)
        # Loop forever or until timeout is over
        next_attempt_window_s = 1
        while loop_forever or (monotonic() <= loop_until):
            now = monotonic()
            try:
                if loop_forever:
                    remaining_time = "-"
                else:
                    remaining_time = int(loop_until - now)

                logging.info("MQTT reconnect attempt (since: %s, remaining time: %s)"
                             % (int(now - start_disconnection), remaining_time))

                ret = self._client.reconnect()
                if ret == mqtt.MQTT_ERR_SUCCESS:
                    break
            except Exception:
                # Retry to connect in current attempt windows range
                delay_s = randrange(next_attempt_window_s, next_attempt_window_s * 2)
                if next_attempt_window_s < 32:
                    next_attempt_window_s = next_attempt_window_s * 2
                logging.debug("Retrying to connect in %d seconds", delay_s)
                # Last sleep may end after max timeout, but not a big issue
                sleep(delay_s)

        if not loop_forever:
            # In case of timeout set, check if it exits because of timeout
            if monotonic() > loop_until:
                logging.error("Unable to reconnect after %s seconds", self.timeout)
                return None

        # Socket must be available once reconnect is successful
        if self._client.socket() is None:
            logging.error("Cannot get socket after reconnect")
            return None
        else:
            logging.info("Successfully acquired socket after reconnect")

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
                try:
                    # check if we are connected
                    # Get client socket to select on it
                    # This function manage the reconnect
                    sock = self._get_socket()
                    if sock is None:
                        # Cannot get the socket, probably an issue
                        # with connection. Exit the thread
                        logging.error("Cannot get MQTT socket, exit...")
                        self.running = False
                    else:
                        self._do_select(sock)
                except TimeoutError:
                    logging.error("Timeout in connection, force a reconnect")
                    self._client.reconnect()
            except Exception:
                # If an exception is not caught before this point
                # All the transport module must be stopped in order to be fully
                # restarted by the managing agent
                logging.exception("Unexpected exception in MQTT wrapper Thread")
                self.running = False

        if self.on_termination_cb is not None:
            # As this thread is daemonized, inform the parent that this
            # thread has exited
            self.on_termination_cb()

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
        self._publish_monitor.on_publish_request()

    def subscribe(self, topic, cb, qos=2) -> None:
        logging.debug("Subscribing to: {}".format(topic))
        self._client.subscribe(topic, qos)
        self._client.message_callback_add(topic, cb)

    @property
    def publish_queue_size(self):
        return self._publish_monitor.get_publish_queue_size()

    @property
    def publish_waiting_time_s(self):
        return self._publish_monitor.get_publish_waiting_time_s()


class SelectableQueue(queue.LifoQueue):
    """
    Wrapper arround a Queue to make it selectable with an associated
    socket and with a built-in rate limit in term of reading

    Args:
        rate_limit_pps: maximum number of get during one second, None for unlimited
    """

    def __init__(self, rate_limit_pps=None):
        super().__init__()
        self._putsocket, self._getsocket = socket.socketpair()
        if rate_limit_pps == 0:
            # 0 is same as no limit
            rate_limit_pps = None
        self.rate_limit_pps = rate_limit_pps
        self._get_ts_list = list()
        self._signal_scheduled = False
        self._signaled = False
        self._signal_lock = Lock()

    def fileno(self):
        """
        Implement fileno to be selectable
        :return: the reception socket fileno
        """
        return self._getsocket.fileno()

    def put(self, item, block=True, timeout=None):
        # Insert item in queue
        super().put(item, block, timeout)
        self._signal()

    def _signal(self, delay_s=0):
        with self._signal_lock:
            if self._signaled:
                return

            if self._signal_scheduled:
                return

            def _signal_with_delay(delay_s):
                sleep(delay_s)
                with self._signal_lock:
                    self._signal_scheduled = False
                    self._putsocket.send(b"x")
                    self._signaled = True

            if delay_s > 0:
                self._signal_scheduled = True
                Thread(target=_signal_with_delay, args=[delay_s]).start()
            else:
                # No delay needed, signal directly
                self._putsocket.send(b"x")
                self._signaled = True

    def _unsignal(self):
        with self._signal_lock:
            self._getsocket.recv(1)
            self._signaled = False

    def _get_current_rate(self):
        # First of all, remove the element that are older than 1 second
        now = monotonic()
        for i in range(len(self._get_ts_list) - 1, -1, -1):
            if (self._get_ts_list[i] + 1) < now:
                del self._get_ts_list[: i + 1]
                break

        return len(self._get_ts_list)

    def _get_next_time(self):
        # Compute when next room will be available
        # in moving window
        # Return value is between 0 and 1

        # Note that _get_current_rate should have been called before
        # so that items are all queued for less than 1s
        now = monotonic()
        if len(self._get_ts_list) > 0:
            queued_time = now - self._get_ts_list[0]
            if queued_time <= 1:
                return 1 - queued_time

            return 0

    def _is_rate_limit_reached(self):
        # Rate limit is computed on last second
        if self.rate_limit_pps is None:
            # No rate control
            return False

        if self._get_current_rate() >= self.rate_limit_pps:
            # We have reached rate limit
            # compute when new room is present
            logging.debug("Over the rate limit still {} paquet queued".format(self.qsize()))
            # How many time remains for first entry
            return True

        return False

    def get(self):
        if self._is_rate_limit_reached():
            # We are over the limit so clear select
            self._unsignal()
            # Start a task to signal available messages
            self._signal(delay_s=self._get_next_time())
            # There is something to get but rate limit is reached
            # so it is empty from consumer point of view
            raise queue.Empty

        # Get item first so get can be called and
        # raise empty exception
        try:
            item = super().get(False, None)
            # If rate limt set, add the get
            if self.rate_limit_pps is not None:
                self._get_ts_list.append(monotonic())

            return item
        except queue.Empty as e:
            self._unsignal()
            raise e


class PublishMonitor:
    """
        Object dedicated to MQTT publish monitoring, in a simple
        and "Thread-safe" way.
    """

    def __init__(self):
        self._lock = Lock()
        self._size = 0
        self._last_publish_event_timestamp = 0  # valid if size != 0

    def get_publish_queue_size(self):
        with self._lock:
            return self._size

    def get_publish_waiting_time_s(self):
        with self._lock:
            if self._size == 0:
                return 0
            else:
                delta = datetime.now() - self._last_publish_event_timestamp
                return delta.total_seconds()

    def on_publish_request(self):
        with self._lock:
            if self._size == 0:
                self._last_publish_event_timestamp = datetime.now()
            self._size = self._size + 1

    def on_publish_done(self):
        with self._lock:
            self._size = self._size - 1
            self._last_publish_event_timestamp = datetime.now()
