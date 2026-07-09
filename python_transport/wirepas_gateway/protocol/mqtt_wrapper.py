# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import logging
import queue
import socket
import ssl
from collections import deque
from select import select
from threading import Thread, Lock
from time import sleep, monotonic
from random import randrange

from paho.mqtt import client as mqtt
from paho.mqtt.client import connack_string

from wirepas_gateway.utils.argument_tools import BufferingAction


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
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            protocol=mqtt.MQTTProtocolVersion.MQTTv311,
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

        max_queue_size = None
        if settings.buffering_action == BufferingAction.DROP_PACKETS:
            max_queue_size = settings.buffering_max_buffered_packets
        self._publish_queue = SelectableQueue(
            rate_limit_pps=settings.mqtt_rate_limit_pps,
            max_size=max_queue_size,
        )
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

    def _on_disconnect(self, client, userdata, rc):
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
        if self._publish_queue.put((topic, payload, qos, retain)):
            # Only count the request if the queue grew. If a queued message was
            # replaced due to queue size limit, the pending message count stays
            # the same.
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


class SelectableQueue:
    """
    LIFO queue made selectable with an associated socket pair
    and with a built-in rate limit in term of reading

    When max_size is given and the limit is reached, each insertion to the
    queue drops the oldest element so that the queue size stays the same.

    Args:
        rate_limit_pps: maximum number of get during one second, None for
                        unlimited
        max_size: maximum number of items the queue can hold. None or 0 for
                  unlimited
    """

    DROP_LOG_PERIOD_S = 60

    def __init__(self, rate_limit_pps=None, max_size=None):
        self._putsocket, self._getsocket = socket.socketpair()
        if rate_limit_pps == 0:
            # 0 is same as no limit
            rate_limit_pps = None
        self.rate_limit_pps = rate_limit_pps
        self._get_ts_list = list()
        self._signal_scheduled = False
        self._signaled = False
        if max_size is not None and max_size <= 0:
            max_size = None
        if max_size is not None:
            logging.info(f"Publish queue size limited to {max_size}")
        self._queue = deque(maxlen=max_size)
        self._dropped_count = 0
        self._last_drop_log_ts = monotonic()
        self._lock = Lock()

    def fileno(self):
        """
        Implement fileno to be selectable
        :return: the reception socket fileno
        """
        return self._getsocket.fileno()

    def put(self, item):
        """
        Insert an item in the queue.

        Returns:
            True if the queue size increased, False if the oldest item was
            dropped to make room for the new one (queue full).
        """
        with self._lock:
            previous_len = len(self._queue)
            self._queue.append(item)
            new_len = len(self._queue)
            increased = previous_len != new_len
            if not increased:
                self._dropped_count += 1
            drop_log = self._check_and_get_drop_log_locked()
            self._signal_locked()

        if drop_log is not None:
            logging.warning(drop_log)

        return increased

    def _check_and_get_drop_log_locked(self):
        if self._dropped_count <= 0:
            return None

        now = monotonic()
        elapsed = now - self._last_drop_log_ts
        if elapsed < self.DROP_LOG_PERIOD_S:
            return None

        report = f"Dropped {self._dropped_count} MQTT messages in the last {int(elapsed)} seconds"
        self._dropped_count = 0
        self._last_drop_log_ts = now

        return report

    def _signal_locked(self):
        if self._signaled or self._signal_scheduled:
            return

        self._putsocket.send(b"x")
        self._signaled = True

    def _schedule_signal_locked(self, delay_s):
        if self._signaled or self._signal_scheduled:
            return

        if delay_s is not None and delay_s > 0:
            self._signal_scheduled = True
            Thread(target=self._signal_after_delay, args=[delay_s]).start()
        else:
            # No delay needed, signal directly
            self._putsocket.send(b"x")
            self._signaled = True

    def _signal_after_delay(self, delay_s):
        sleep(delay_s)
        with self._lock:
            self._signal_scheduled = False
            self._putsocket.send(b"x")
            self._signaled = True

    def _consume_signal_locked(self):
        if self._signaled:
            self._getsocket.recv(1)
            self._signaled = False

    def _get_current_rate_locked(self):
        # First of all, remove the element that are older than 1 second
        now = monotonic()
        for i in range(len(self._get_ts_list) - 1, -1, -1):
            if (self._get_ts_list[i] + 1) < now:
                del self._get_ts_list[: i + 1]
                break

        return len(self._get_ts_list)

    def _get_next_time_locked(self):
        # Compute when next room will be available
        # in moving window
        # Return value is between 0 and 1

        # Note that _get_current_rate_locked should have been called before
        # so that items are all queued for less than 1s
        now = monotonic()
        if len(self._get_ts_list) > 0:
            queued_time = now - self._get_ts_list[0]
            if queued_time <= 1:
                return 1 - queued_time

            return 0

    def _is_rate_limit_reached_locked(self):
        # Rate limit is computed on last second
        if self.rate_limit_pps is None:
            # No rate control
            return False

        if self._get_current_rate_locked() >= self.rate_limit_pps:
            # We have reached rate limit
            # compute when new room is present
            logging.debug("Over the rate limit still {} paquet queued".format(len(self._queue)))
            # How many time remains for first entry
            return True

        return False

    def get(self):
        """
        Get the most recent item from the queue.

        Raises:
            queue.Empty if there is nothing to get or the rate limit is reached
        """
        with self._lock:
            if self._is_rate_limit_reached_locked():
                # We are over the limit so clear select
                self._consume_signal_locked()
                # Start a task to signal available messages
                self._schedule_signal_locked(self._get_next_time_locked())
                # There is something to get but rate limit is reached
                # so it is empty from consumer point of view
                raise queue.Empty

            # Get item first so pop can be called and
            # raise empty exception
            try:
                item = self._queue.pop()
            except IndexError:
                self._consume_signal_locked()
                raise queue.Empty

            # If rate limit set, add the get
            if self.rate_limit_pps is not None:
                self._get_ts_list.append(monotonic())

            return item


class PublishMonitor:
    """
    Thread-safe monitor for outstanding MQTT publishes.

    "Size" is the number of publishes that have been requested
    (on_publish_request) but not yet completed (on_publish_done, i.e.
    acknowledged by the MQTT broker).

    It is NOT the number of items currently held in MQTTWrapper._publish_queue.
    An item stays counted from the moment it is requested until the broker
    confirms it, including while it sits in the queue and while it is in flight
    to the broker.

    It also keeps the timestamp of the last publish event, used to measure how
    long publishing has been stalled (i.e. disconnected from broker).
    """

    def __init__(self):
        self._lock = Lock()
        self._size = 0
        self._last_publish_event_timestamp = 0  # valid if size != 0

    def get_publish_queue_size(self):
        """
        Return the number of publishes requested but not yet completed.
        """
        with self._lock:
            return self._size

    def get_publish_waiting_time_s(self):
        """
        Return the seconds elapsed since the last publish event while publishes
        are still outstanding, or 0 if none are pending. A growing value means
        publishing is stalled.
        """
        with self._lock:
            if self._size == 0:
                return 0
            else:
                return monotonic() - self._last_publish_event_timestamp

    def on_publish_request(self):
        """
        Register that a publish has been requested.
        """
        with self._lock:
            if self._size == 0:
                self._last_publish_event_timestamp = monotonic()
            self._size = self._size + 1

    def on_publish_done(self):
        """
        Register that a publish has completed (acknowledged by the broker).
        """
        with self._lock:
            self._size = self._size - 1
            self._last_publish_event_timestamp = monotonic()
