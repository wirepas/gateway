"""
    Log tools
    ==========

    Contains multipurpose utilities for interfacing with the logging
    facilities

    .. Copyright:
        Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

import sys
import logging


class LoggerHelper:
    """
    LoggerHelper

    The loggerhelper is a class to abstract the creation of logger
    instances.
    """

    def __init__(self, module_name, level: str = "debug", **kwargs):
        super(LoggerHelper, self).__init__()

        self._logger = logging.getLogger(module_name)
        self._name = module_name
        self._level = "{0}".format(level.upper())
        self._handlers = dict()

        self._log_format = dict()
        self._log_format["stdout"] = logging.Formatter(
            "%(asctime)s | [%(levelname)s] %(name)s@%(filename)s:%(lineno)d:%(message)s"
        )

        self._log_format["stderr"] = logging.Formatter(
            "%(asctime)s | [%(levelname)s] %(name)s@%(filename)s:%(lineno)d:%(message)s"
        )

        try:
            self._logger.setLevel(getattr(logging, self._level))
        except AttributeError:
            self._logger.setLevel(logging.DEBUG)

    @property
    def level(self):
        """ Return the logging level """
        return self._level

    @level.setter
    def level(self, value):
        """ Sets the log level """
        self._level = "{0}".format(value.upper())

        try:
            self._logger.setLevel(getattr(logging, self._level))
        except AttributeError:
            self._logger.setLevel(logging.DEBUG)

    def format(self, name):
        """ Return the format for a known stream """
        return self._log_format[name]

    def add_stdout(self):
        """ Adds a handler for stdout """
        try:
            if self._handlers["stdout"]:
                self._handlers["stdout"].close()
        except KeyError:
            self._handlers["stdout"] = None

        self._handlers["stdout"] = logging.StreamHandler(stream=sys.stdout)
        self._handlers["stdout"].setFormatter(self.format("stdout"))
        self._logger.addHandler(self._handlers["stdout"])

    def add_stderr(self, value="error"):
        """ Adds a handler for stderr """
        try:
            if self._handlers["stderr"]:
                self._handlers["stderr"].close()
        except KeyError:
            self._handlers["stderr"] = None

        self._handlers["stderr"] = logging.StreamHandler(stream=sys.stderr)
        self._handlers["stderr"].setFormatter(self.format("stderr"))
        # By default stderr handler limits logging level to error.
        # In case logger itself has higher value, e.g. critical,
        # it will limit the input of this handler.
        try:
            level = "{0}".format(value.upper())
            self._handlers["stderr"].setLevel(getattr(logging, level))
        except AttributeError:
            self._handlers["stderr"].setLevel(logging.ERROR)
        self._logger.addHandler(self._handlers["stderr"])

    def setup(self, level: str = None, propagate=False):
        """
        Constructs the logger with the system arguments provided upon
        the object creation.
        """

        if level is not None:
            self.level = level

        self.add_stdout()
        self._logger.propagate = propagate

        return self._logger

    def add_custom_level(self, debug_level_name, debug_level_number):
        """ Add a custom debug level for log filtering purposes.
            To set a logging level called sensitive please call

            self.add_custom_level(debug_level_name='sensitive',
                                  debug_level_number=100)

            afterwards the method will be available to the logger as

            logger.sensitive('my logging message')
        """

        logging.addLevelName(debug_level_number, debug_level_name.upper())

        def cb(self, message, *pargs, **kws):
            # Yes, logger takes its '*pargs' as 'args'.
            if self.isEnabledFor(debug_level_number):
                self._log(debug_level_number, message, pargs, **kws)

        setattr(logging.Logger, debug_level_name, cb)

    def close(self):
        """ Attempts to close log handlers """
        for _, handler in self._handlers.items():
            try:
                handler.close()
            except Exception as err:
                self._logger.exception("Could not close logger %s", err)
