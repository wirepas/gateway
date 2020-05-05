# Copyright 2020 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

from threading import Thread, Event, Lock
from datetime import datetime, timedelta


class MessageQueue(Thread):
    def __init__(
        self,
        logger,
        on_multi_packet_ready_cb,
        dst_endpoints=None,
        max_packets=0,
        max_size=0,
        max_queuing_time_s=0,
        filter_name="No name",
    ):
        Thread.__init__(self)
        # Daemonize thread to exit with full process
        self.daemon = True

        self.logger = logger

        if dst_endpoints.__len__() == 0:
            self.logger.error(
                "Cannot create a group of packets without endpoint criteria"
            )
            raise ValueError

        if max_packets == 0 and max_size == 0 and max_queuing_time_s == 0:
            self.logger.error(
                "Group of packets need at least one criteria to end grouping"
            )
            raise ValueError

        self.endpoints = dst_endpoints
        self.max_packets = max_packets
        self.max_size = max_size
        self.max_queing_time_s = max_queuing_time_s
        self.filter_name = filter_name

        self.running = False
        self.message_received_event = Event()
        self.message_received_event.clear()

        self._messages_list = []
        self._next_expiration_date = None

        self._flush = False
        # Lock to protect the list
        self._lock = Lock()

        self.on_packets_ready_cb = on_multi_packet_ready_cb

        self.logger.debug(
            'Group "%s" created with param: delay=%s max_p=%s max_s=%s'
            % (
                self.filter_name,
                self.max_queing_time_s,
                self.max_packets,
                self.max_size,
            )
        )

    def is_message_for_me(self, dst_endpoint):
        if self.endpoints is None or dst_endpoint in self.endpoints:
            self.logger.debug("Packet match filter %s" % self.filter_name)
            return True
        return False

    def flush(self):
        # Force a send of what the queue contain
        self._flush = True
        self.message_received_event.set()

    def queue_message(self, message):
        # Queue the message
        with self._lock:
            if len(self._messages_list) == 0 and self.max_queing_time_s >= 0:
                # No message in queue yet, so take the current timestamp
                self._next_expiration_date = datetime.now() + timedelta(
                    seconds=self.max_queing_time_s
                )
                self.logger.debug(
                    "Set next expiration date to %s" % self._next_expiration_date
                )

            self._messages_list.append(message)

            # Notify the other thread that a message was received
            self.message_received_event.set()

    def run(self):
        """
        Main queue loop that is in charge of creating and sending the packet when needed
        """
        self.running = True
        while self.running:
            # Compute timeout for next execution:
            now = datetime.now()
            if self._next_expiration_date is None:
                timeout = None
            elif self._next_expiration_date < now:
                # It should never happen
                timeout = 0
            else:
                timeout = (self._next_expiration_date - now).total_seconds()

            self.logger.debug(
                "Filter %s: waiting for again %s" % (self.filter_name, timeout)
            )

            self.message_received_event.wait(timeout)

            with self._lock:
                # Check what happen
                now = datetime.now()
                send = False
                if self.message_received_event.is_set():
                    # We received a new message
                    # Is max packet reached
                    if len(self._messages_list) >= self.max_packets:
                        self.logger.debug(
                            "SEND: limit reached: %d packet in list vs %s"
                            % (len(self._messages_list), self.max_packets)
                        )
                        send = True

                    # Max size reached
                    # TODO evaluate full size packet

                    # Is it time to flush
                    if self._flush:
                        self.logger.debug("SEND: Flush")
                        send = True

                    # Clear the event
                    self.message_received_event.clear()

                # Max delay reached
                if now >= self._next_expiration_date:
                    self.logger.debug("SEND: expiration date")
                    send = True

                if send:
                    if self.on_packets_ready_cb(self._messages_list, self.filter_name):
                        # Reset counter and list
                        self._next_expiration_date = None
                        self._messages_list.clear()
