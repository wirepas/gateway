# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
from time import time
from threading import Lock


class CacheMessage:
    """
    Class to cache messages to avoid sending duplicates in MQTT with QoS=1.
    """
    def __init__(
        self,
        cache_time_window,
        cache_update_s
    ):
        """
        Args:
            cache_time_window: time in seconds after which a message is clean from the cache.
            cache_update_s: period in seconds to update the list of received messages.
                            Must be shorter than cache_time_window
        """
        self._lock = Lock()
        self.msg_list = dict()  # Dictionary of received messages id mapped to their timestamps

        self.cache_time_window = cache_time_window
        self.cache_update_s = min(cache_update_s, cache_time_window)

        self.last_update_time = 0  # last time an update of the list of received messages was done

    def add_msg(self, msg_id):
        """
        Adds a received message to the cache.
        If the message is a duplicate, it only updates its last timestamp to the current time.

        Args:
            msg_id: the id of a message to be added to the cache.
        """
        current_time = time()
        with self._lock:
            if current_time - self.last_update_time > self.cache_update_s:
                self._clean_msg_list()

            is_duplicate = self.is_in_cache(msg_id)
            self.msg_list[msg_id] = current_time
            return not is_duplicate

    def get_size(self):
        """
        Returns the number of messages in the cache.
        """
        with self._lock:
            return len(self.msg_list)

    def _clean_msg_list(self):
        """
        Clean the old messages in the cache
        based on the time window cache_time_window attribute.
        """
        current_time = time()
        self.msg_list = {
            msg_id: msg_time for (msg_id, msg_time) in self.msg_list.items()
            if current_time - msg_time <= self.cache_time_window
        }
        self.last_update_time = current_time

    def is_in_cache(self, msg_id):
        """
        Returns True if the id of a message is already in the cache.
        Return False otherwise.

        Args:
            msg_id: id of the message received
        """
        return msg_id in self.msg_list
