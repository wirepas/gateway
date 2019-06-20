"""
    Wirepas Gateway Client
    =========================================

    This module is property of Wirepas Oy and is meant for its user. Usage
    implies knowledge and acceptance of the license agreement provided
    through the separate channels.

    The goal of this module is to support the exchange of data from a
    Wirepas gateway to a Wirepas or user backend system.

    .. Style guidelines:
       http://google.github.io/styleguide/pyguide.html

    .. Attributes defined from _PEP 484:
       https://www.python.org/dev/peps/pep-0484/

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0
        See file LICENSE for full license details.
"""
try:
    from . import dbus
except ImportError:
    pass

try:
    from . import protocol
except ImportError:
    pass

try:
    from . import utils
except ImportError:
    pass

__title__ = "wirepas_messaging"
__version__ = "1.2.0rc1"
