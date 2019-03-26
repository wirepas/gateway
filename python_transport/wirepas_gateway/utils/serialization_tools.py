"""
    Serialization tools
    ===================

    Contains multipurpose utilities for serializing objects .

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

import json
import datetime


def serialize(obj) -> str:
    """ Serializes an object into json """
    return json.dumps(obj, default=json_serial, sort_keys=True, indent=4)


def json_serial(obj) -> str:
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    if isinstance(obj, (bytearray, bytes)):
        return binascii.hexlify(obj)
    if isinstance(obj, set):
        return str(obj)

    raise TypeError("Type %s not serializable" % type(obj))
