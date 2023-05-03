# Copyright 2022 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
from time import time, sleep
from threading import Lock, Thread


class MessageCache:
    """
    Class to cache all recent messages to avoid sending duplicates in MQTT.
    """
    def __init__(
        self,
        cache_time_window_s,
        cache_update_s
    ):
        """
        Args:
            cache_time_window_s: time in seconds after which a message is removed from the cache.
            cache_update_s: period in seconds to update the list of received messages.
                            Must be shorter than cache_time_window_s
        """
        self._lock = Lock()
        # Dictionary of received messages id mapped to their timestamps
        self._cache = dict()
        # last time an update of the list of received messages was done
        self._last_update_time = 0

        self.cache_time_window_s = cache_time_window_s
        self.cache_update_s = min(cache_update_s, cache_time_window_s)

        # Start a thread that cleans periodically the cache.
        self._clean_cache_thread = Thread(target=self._clean_cache_thread, daemon=True)
        self._clean_cache_thread.start()

    def add_msg(self, msg_id):
        """
        Adds a received message to the cache. If the message is a duplicate,
        it only updates its last timestamp to the current time.

        Args:
            msg_id: the id of a message to be added to the cache.
        """
        current_time = time()
        is_duplicate = self.is_in_cache(msg_id)
        with self._lock:
            self._cache[msg_id] = current_time
        return not is_duplicate

    def get_size(self):
        """
        Returns the number of messages in the cache.
        """
        with self._lock:
            return len(self._cache)

    def _clean_cache(self):
        """
        Clean the old messages in the cache
        based on the time window cache_time_window_s attribute.
        """
        with self._lock:
            current_time = time()
            self._cache = {
                msg_id: msg_time for (msg_id, msg_time) in self._cache.items()
                if current_time - msg_time <= self.cache_time_window_s
            }
            self._last_update_time = current_time

    def _clean_cache_thread(self):
        """
        Clean the cache and sleep cache_update_s seconds in loop.
        """
        while True:
            self._clean_cache()
            sleep(self.cache_update_s)

    def is_in_cache(self, msg_id):
        """
        Return True if the id of a message is already in the cache, False otherwise.

        Args:
            msg_id: id of the message
        """
        with self._lock:
            return msg_id in self._cache
