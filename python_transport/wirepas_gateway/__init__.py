"""
    Wirepas Gateway
    ===============

    .. Style guidelines:
       http://google.github.io/styleguide/pyguide.html

    .. Copyright:
        Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
        See file LICENSE for full license details.
"""
# flake8: noqa

from . import dbus
from . import protocol
from . import utils
import importlib.metadata

from .__about__ import (
    __author__,
    __author_email__,
    __classifiers__,
    __copyright__,
    __description__,
    __license__,
    __pkg_name__,
    __title__,
    __url__,
    __keywords__,
)

__version__ = importlib.metadata.version(__pkg_name__)

