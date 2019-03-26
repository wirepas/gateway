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

__author__ = "Wirepas Oy"

from . import dbus
from . import protocol
from . import utils
