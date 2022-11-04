from time import sleep
from wirepas_gateway.protocol.cache_message import CacheMessage

CACHE_TIME_WINDOW = 0.1
CACHE_UPDATE_S = 0.025
REQ_ID = 160
REQ_ID2 = 161


def test_adding_msg():
    """
    Tests the adding of message in the cache.
    """
    cache = CacheMessage(CACHE_TIME_WINDOW, CACHE_UPDATE_S)
    assert cache.get_size() == 0

    assert cache.add_msg(REQ_ID) is True
    assert cache.get_size() == 1

    assert cache.add_msg(REQ_ID2) is True
    assert cache.get_size() == 2

    # Test the mapping in the cache
    assert cache.is_in_cache(REQ_ID)
    assert cache.is_in_cache(REQ_ID2)

def test_duplicate():
    """
    Tests if the duplicate messages are not stored
    """
    cache = CacheMessage(CACHE_TIME_WINDOW, CACHE_UPDATE_S)
    assert cache.get_size() == 0

    assert cache.add_msg(REQ_ID) is True
    assert cache.get_size() == 1
    time1 = cache.msg_list[REQ_ID]

    # Test if a redundant message is dropped
    assert cache.add_msg(REQ_ID) is False
    assert cache.get_size() == 1

    # Test if the timestamp of the message has been updated
    time2 = cache.msg_list[REQ_ID]
    assert time1 != time2

def test_cache_time_window():
    """
    Tests the well functionning of cache time window.
    """
    cache = CacheMessage(CACHE_TIME_WINDOW, CACHE_UPDATE_S)
    assert cache.add_msg(REQ_ID) is True

    # Test if the cache has reset eventually
    sleep(CACHE_TIME_WINDOW)
    assert cache.add_msg(REQ_ID) is True
