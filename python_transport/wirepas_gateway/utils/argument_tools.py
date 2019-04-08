"""
    Arguments
    =========

    Contains helpers to parse application arguments

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0
        See file LICENSE for full license details.
"""


import json
import logging
import argparse
import datetime
import time
import yaml
import ssl
import pkg_resources

from .serialization_tools import serialize


class Settings(object):
    """Simple class to handle library settings"""

    def __init__(self, settings: dict):
        super(Settings, self).__init__()
        for k, v in settings.items():
            self.__dict__[k] = v

    def items(self):
        return self.__dict__.items()

    @classmethod
    def from_args(cls, args, skip_undefined=True):
        settings = dict()

        try:
            if args.settings:
                with open(args.settings, "r") as f:
                    settings = yaml.load(f)
        except:
            pass

        for key, value in args.__dict__.items():
            if value is not None or skip_undefined is False:
                if key in settings and settings[key] is None:
                    settings[key] = value
                if key not in settings:
                    settings[key] = value

        return cls(settings)

    def __str__(self):
        return str(self.__dict__)


class ParserHelper(object):
    """
    ParserHelper

    Handles the creation and decoding of arguments

    """

    def __init__(
        self,
        description="argument parser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    ):
        super(ParserHelper, self).__init__()
        self._parser = argparse.ArgumentParser(
            description=description, formatter_class=formatter_class
        )

        self._groups = dict()

    @property
    def parser(self):
        """ Returns the parser object """
        return self._parser

    @property
    def arguments(self):
        """ Returns arguments that it can parse and throwing an error otherwise """
        self._arguments = self.parser.parse_args()
        return self._arguments

    @property
    def known_arguments(self):
        """ returns the unknown arguments it could not parse """
        self._arguments, self._unknown_arguments = self.parser.parse_known_args()
        return self._arguments

    @property
    def unkown_arguments(self):
        """ returns the unknown arguments it could not parse """
        return self._unknown_arguments

    def settings(self, settings_class=None, skip_undefined=True) -> "Settings":
        self._arguments = self.parser.parse_args()

        if settings_class is None:
            settings_class = Settings

        settings = settings_class.from_args(self._arguments, skip_undefined)

        return settings

    def __getattr__(self, name):
        if name not in self._groups:
            self._groups[name] = self._parser.add_argument_group(name)

        return self._groups[name]

    def add_file_settings(self):
        """ For file setting handling"""
        self.file_settings.add_argument(
            "--settings",
            type=str,
            required=False,
            default="settings.yml",
            help="settings file.",
        )

    def add_transport(self):
        """ Transport module arguments """
        self.transport.add_argument(
            "-s", "--host", default=None, type=str, help="MQTT broker address"
        )

        self.transport.add_argument(
            "-p", "--port", default=8883, type=int, help="MQTT broker port"
        )

        self.transport.add_argument(
            "-u", "--username", default=None, type=str, help="MQTT broker username"
        )

        self.transport.add_argument(
            "-pw", "--password", default=None, type=str, help="MQTT broker password"
        )

        self.transport.add_argument(
            "-t",
            "--tlsfile",
            default=None,
            help="MQTT broker tls cert file. Optional in case system certificates"
            " are not up to date",
        )

        self.transport.add_argument(
            "-ua",
            "--unsecure_authentication",
            default=False,
            action="store_true",
            help="Disable TLS secure authentication to the server",
        )

        self.transport.add_argument(
            "-i", "--gwid", default=None, type=str, help="Id of the gateway"
        )

        self.transport.add_argument(
            "-fp",
            "--full_python",
            default=False,
            action="store_true",
            help="Do not use C extension for optimization",
        )

        self.transport.add_argument(
            "-gm", "--gateway_model", default=None, help="Model name of the gateway"
        )

        self.transport.add_argument(
            "-gv", "--gateway_version", default=None, help="Version of the gateway"
        )

        self.transport.add_argument(
            "-iepf",
            "--ignored_endpoints_filter",
            default=None,
            help="Destination endpoints list to ignore (not published)",
        )

        self.transport.add_argument(
            "-wepf",
            "--whitened_endpoints_filter",
            default=None,
            help="Destination endpoints list to whiten (no payload content, only size)",
        )

    def dump(self, path):
        """ dumps the arguments into a file """
        with open(path, "w") as f:
            f.write(serialize(vars(self._arguments)))
