from time import sleep
from wirepas_gateway.protocol.message_cache import MessageCache

CACHE_TIME_WINDOW_S = 0.1
CACHE_UPDATE_S = 0.025
REQ_ID = 160
REQ_ID2 = 161


def test_adding_msg():
    """
    Tests the adding of message in the cache.
    """
    message_cache = MessageCache(CACHE_TIME_WINDOW_S, CACHE_UPDATE_S)
    assert message_cache.get_size() == 0

    assert message_cache.add_msg(REQ_ID) is True
    assert message_cache.get_size() == 1

    assert message_cache.add_msg(REQ_ID2) is True
    assert message_cache.get_size() == 2

    # Test the mapping in the cache
    assert message_cache.is_in_cache(REQ_ID)
    assert message_cache.is_in_cache(REQ_ID2)


def test_duplicate():
    """
    Tests if the duplicate messages are not stored
    """
    message_cache = MessageCache(CACHE_TIME_WINDOW_S, CACHE_UPDATE_S)
    assert message_cache.get_size() == 0

    assert message_cache.add_msg(REQ_ID) is True
    assert message_cache.get_size() == 1

    # Test if a redundant message is dropped
    assert message_cache.add_msg(REQ_ID) is False
    assert message_cache.get_size() == 1


def test_cache_time_window():
    """
    Tests the well functionning of cache time window.
    """
    message_cache = MessageCache(CACHE_TIME_WINDOW_S, CACHE_UPDATE_S)
    assert message_cache.add_msg(REQ_ID) is True

    # Test if the cache has reset eventually
    sleep(CACHE_TIME_WINDOW_S/2)
    assert message_cache.is_in_cache(REQ_ID) is True
    sleep(CACHE_TIME_WINDOW_S)
    assert message_cache.is_in_cache(REQ_ID) is False

    # And that a message with the same id can be added after the time window
    assert message_cache.add_msg(REQ_ID) is True
