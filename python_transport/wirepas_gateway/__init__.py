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

__author__ = "Wirepas Ltd"
__author_email__ = "opensource@wirepas.com"
__classifiers__ = [
    "Development Status :: 5 - Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Topic :: Software Development :: Libraries",
    "Programming Language :: Python :: 3",
]
__copyright__ = "2019 Wirepas Ltd"
__description__ = "Wirepas gateway transport service that connects the local dbus to a remote MQTT broker."
__license__ = "Apache-2"
__name__ = "wirepas_gateway"
__title__ = "Wirepas Gateway Transport Service"
__url__ = "https://github.com/wirepas/gateway"
__version__ = "1.2.0rc1"
__keywords__ = "wirepas connectivity iot mesh"
