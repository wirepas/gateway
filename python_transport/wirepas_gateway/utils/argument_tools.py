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
            help="settings file",
        )

    def add_mqtt(self):
        """ Commonly used MQTT arguments """
        self.mqtt.add_argument(
            "--mqtt_hostname",
            default=None,
            action="store",
            type=str,
            help="MQTT broker hostname ",
        )

        self.mqtt.add_argument(
            "--mqtt_username",
            default=None,
            action="store",
            type=str,
            help="MQTT broker username ",
        )

        self.mqtt.add_argument(
            "--mqtt_password",
            default=None,
            action="store",
            type=str,
            help="MQTT broker password",
        )

        self.mqtt.add_argument(
            "--mqtt_port",
            default=8883,
            action="store",
            type=int,
            help="MQTT broker port",
        )

        self.mqtt.add_argument(
            "--mqtt_ca_certs",
            default=None,
            action="store",
            type=str,
            help=(
                "A string path to the Certificate "
                "Authority certificate files that "
                "are to be treated as trusted by "
                "this client"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_certfile",
            default=None,
            action="store",
            type=str,
            help=("Strings pointing to the PEM encoded client certificate"),
        )

        self.mqtt.add_argument(
            "--mqtt_keyfile",
            default=None,
            action="store",
            type=str,
            help=(
                "Strings pointing to the PEM "
                "encoded client private keys "
                "respectively"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_cert_reqs",
            default=ssl.CERT_REQUIRED,
            action="store",
            type=str,
            help=(
                "Defines the certificate "
                "requirements that the client "
                "imposes on the broker"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_tls_version",
            default=ssl.PROTOCOL_TLSv1_2,
            action="store",
            type=str,
            help=("Specifies the version of the SSL / TLS protocol to be used"),
        )

        self.mqtt.add_argument(
            "--mqtt_ciphers",
            default=None,
            action="store",
            type=str,
            help=(
                "A string specifying which "
                "encryption ciphers are allowable "
                "for this connection"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_persist_session",
            default=True,
            action="store_true",
            help=(
                "When False the broker will buffer "
                "session packets between "
                "reconnection"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_force_unsecure",
            default=False,
            action="store_true",
            help=("When True the broker will skip the TLS handshake"),
        )

        self.mqtt.add_argument(
            "--mqtt_allow_untrusted",
            default=False,
            action="store_true",
            help=("When true the client will skip the TLS check"),
        )

    @staticmethod
    def _deprecated_message(new_arg_name):
        return "Deprecated argument (It will be dropped from version 2.x onwards) please use --{} instead".format(
            new_arg_name
        )

    def add_deprecated_args(self):
        """ Deprecated mqtt arguments in order to keep backward compatibility """
        self.deprecated.add_argument(
            "-s",
            "--host",
            default=None,
            type=str,
            help=ParserHelper._deprecated_message("mqtt_hostname"),
        )

        self.deprecated.add_argument(
            "-p",
            "--port",
            default=8883,
            type=int,
            help=ParserHelper._deprecated_message("mqtt_port"),
        )

        self.deprecated.add_argument(
            "-u",
            "--username",
            default=None,
            type=str,
            help=ParserHelper._deprecated_message("mqtt_username"),
        )

        self.deprecated.add_argument(
            "-pw",
            "--password",
            default=None,
            type=str,
            help=ParserHelper._deprecated_message("mqtt_password"),
        )

        self.deprecated.add_argument(
            "-t",
            "--tlsfile",
            default=None,
            help=ParserHelper._deprecated_message("mqtt_certfile"),
        )

        self.deprecated.add_argument(
            "-ua",
            "--unsecure_authentication",
            default=False,
            action="store_true",
            help=ParserHelper._deprecated_message("mqtt_force_unsecure"),
        )

        self.deprecated.add_argument(
            "-i",
            "--gwid",
            default=None,
            type=str,
            help=ParserHelper._deprecated_message("gateway_id"),
        )

    def add_gateway_config(self):
        self.gateway.add_argument(
            "--gateway_id",
            default=None,
            type=str,
            help=("Id of the gateway. It must be unique on same broker"),
        )

        self.gateway.add_argument(
            "-fp",
            "--full_python",
            default=False,
            action="store_true",
            help=("Do not use C extension for optimization"),
        )

        self.gateway.add_argument(
            "-gm", "--gateway_model", default=None, help=("Model name of the gateway")
        )

        self.gateway.add_argument(
            "-gv", "--gateway_version", default=None, help=("Version of the gateway")
        )

    def add_filtering_config(self):
        self.filtering.add_argument(
            "-iepf",
            "--ignored_endpoints_filter",
            default=None,
            help=("Destination endpoints list to ignore (not published)"),
        )

        self.filtering.add_argument(
            "-wepf",
            "--whitened_endpoints_filter",
            default=None,
            help=(
                "Destination endpoints list to whiten "
                "(no payload content, only size)"
            ),
        )

    def dump(self, path):
        """ dumps the arguments into a file """
        with open(path, "w") as f:
            f.write(serialize(vars(self._arguments)))
