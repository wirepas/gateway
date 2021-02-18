"""
    Arguments
    =========

    Contains helpers to parse application arguments

    .. Copyright:
        Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

import argparse
import sys
import os
import yaml

from .serialization_tools import serialize


class Settings:
    """Simple class to handle library settings"""

    def __init__(self, settings: dict):
        super(Settings, self).__init__()
        for k, v in settings.items():
            self.__dict__[k] = v

    def items(self):
        return self.__dict__.items()

    def __str__(self):
        return str(self.__dict__)


class ParserHelper:
    """
    ParserHelper

    Handles the creation and decoding of arguments

    """

    # These options are deprecated but might still be received through the
    # settings file
    _short_options = [
        "s",
        "p",
        "u",
        "pw",
        "t",
        "ua",
        "i",
        "fp",
        "gm",
        "gv",
        "iepf",
        "wepf",
    ]

    def __init__(
        self,
        description="argument parser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        version=None,
    ):
        super(ParserHelper, self).__init__()
        self._parser = argparse.ArgumentParser(
            description=description, formatter_class=formatter_class
        )

        self._groups = dict()
        self._unknown_arguments = None
        self._arguments = None

        if version is not None:
            self.main.add_argument("--version", action="version", version=version)

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

    def settings(self, settings_class=None):
        """ Reads an yaml settings file and puts it through argparse """

        # Parse args from cmd line to see if a custom setting file is specified
        self._arguments = self.parser.parse_args()

        if self._arguments.settings is not None:
            with open(self._arguments.settings, "r") as f:
                settings = yaml.load(f, Loader=yaml.FullLoader)
                arglist = list()

                # Add the file parameters
                for key, value in settings.items():
                    if key in self._short_options:
                        key = "-{}".format(key)
                    else:
                        key = "--{}".format(key)

                    # We assume that booleans are always handled with
                    # store_true. This logic will fail otherwise.
                    if value is False:
                        continue

                    arglist.append(key)

                    # do not append True as the key is enough
                    if value is True:
                        continue
                    arglist.append(str(value))

                arguments = sys.argv
                argument_index = 1  # wm-gw
                if "python" in arguments[0]:  # pythonX transport (...)
                    if "-m" in arguments[1]:  # pythonX -m transport (...)
                        argument_index += 1
                    argument_index = +1
                # Add the cmd line parameters. They will override
                # parameters from file if set in both places.
                for arg in arguments[argument_index:]:
                    arglist.append(arg)

            # Override self._arguments as there are parameters from file
            self._arguments = self.parser.parse_args(arglist)

        if settings_class is None:
            settings_class = Settings

        settings = settings_class(self._arguments.__dict__)

        return settings

    def __getattr__(self, name):
        if name not in self._groups:
            self._groups[name] = self._parser.add_argument_group(name)

        return self._groups[name]

    @staticmethod
    def str2bool(value):
        """ Ensures string to bool conversion """
        if isinstance(value, bool):
            return value
        if value.lower() in ("yes", "true", "t", "y", "1"):
            return True
        elif value.lower() in ("no", "false", "f", "n", "0", ""):
            return False
        else:
            raise argparse.ArgumentTypeError("Boolean value expected.")

    @staticmethod
    def str2int(value):
        """ Ensures string to bool conversion """
        try:
            value = int(value)
        except ValueError:
            if value == "":
                value = 0
            else:
                raise argparse.ArgumentTypeError("Integer value expected.")
        return value

    @staticmethod
    def str2none(value):
        """ Ensures string to bool conversion """
        if value == "":
            return None
        return value

    def add_file_settings(self):
        """ For file setting handling"""
        self.file_settings.add_argument(
            "--settings",
            type=self.str2none,
            required=False,
            default=os.environ.get("WM_GW_FILE_SETTINGS", None),
            help="A yaml file with argument parameters (see help for options).",
        )

    def add_mqtt(self):
        """ Commonly used MQTT arguments """
        self.mqtt.add_argument(
            "--mqtt_hostname",
            default=os.environ.get("WM_SERVICES_MQTT_HOSTNAME", None),
            action="store",
            type=self.str2none,
            help="MQTT broker hostname.",
        )

        self.mqtt.add_argument(
            "--mqtt_username",
            default=os.environ.get("WM_SERVICES_MQTT_USERNAME", None),
            action="store",
            type=self.str2none,
            help="MQTT broker username.",
        )

        self.mqtt.add_argument(
            "--mqtt_password",
            default=os.environ.get("WM_SERVICES_MQTT_PASSWORD", None),
            action="store",
            type=self.str2none,
            help="MQTT broker password.",
        )

        self.mqtt.add_argument(
            "--mqtt_port",
            default=os.environ.get("WM_SERVICES_MQTT_PORT", 8883),
            action="store",
            type=self.str2int,
            help="MQTT broker port.",
        )

        self.mqtt.add_argument(
            "--mqtt_ca_certs",
            default=os.environ.get("WM_SERVICES_MQTT_CA_CERTS", None),
            action="store",
            type=self.str2none,
            help=(
                "A string path to the Certificate "
                "Authority certificate files that "
                "are to be treated as trusted by "
                "this client."
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_certfile",
            default=os.environ.get("WM_SERVICES_MQTT_CLIENT_CRT", None),
            action="store",
            type=self.str2none,
            help=("Strings pointing to the PEM encoded client certificate."),
        )

        self.mqtt.add_argument(
            "--mqtt_keyfile",
            default=os.environ.get("WM_SERVICES_MQTT_CLIENT_KEY", None),
            action="store",
            type=self.str2none,
            help=(
                "Strings pointing to the PEM "
                "encoded client private keys "
                "respectively."
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_cert_reqs",
            default=os.environ.get("WM_SERVICES_MQTT_CERT_REQS", "CERT_REQUIRED"),
            choices=["CERT_REQUIRED", "CERT_OPTIONAL", "CERT_NONE"],
            action="store",
            type=self.str2none,
            help=(
                "Defines the certificate "
                "requirements that the client "
                "imposes on the broker."
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_tls_version",
            default=os.environ.get("WM_SERVICES_MQTT_TLS_VERSION", "PROTOCOL_TLSv1_2"),
            choices=[
                "PROTOCOL_TLS",
                "PROTOCOL_TLS_CLIENT",
                "PROTOCOL_TLS_SERVER",
                "PROTOCOL_TLSv1",
                "PROTOCOL_TLSv1_1",
                "PROTOCOL_TLSv1_2",
            ],
            action="store",
            type=self.str2none,
            help=("Specifies the version of the SSL / TLS protocol to be used."),
        )

        self.mqtt.add_argument(
            "--mqtt_ciphers",
            default=os.environ.get("WM_SERVICES_MQTT_CIPHERS", None),
            action="store",
            type=self.str2none,
            help=(
                "A string specifying which "
                "encryption ciphers are allowable "
                "for this connection."
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_persist_session",
            default=os.environ.get("WM_SERVICES_MQTT_PERSIST_SESSION", False),
            type=self.str2bool,
            nargs="?",
            const=True,
            help=(
                "When True the broker will buffer session packets "
                "between reconnection."
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_force_unsecure",
            default=os.environ.get("WM_SERVICES_MQTT_FORCE_UNSECURE", False),
            type=self.str2bool,
            nargs="?",
            const=True,
            help=("When True the broker will skip the TLS handshake."),
        )

        self.mqtt.add_argument(
            "--mqtt_allow_untrusted",
            default=os.environ.get("WM_SERVICES_MQTT_ALLOW_UNTRUSTED", False),
            type=self.str2bool,
            nargs="?",
            const=True,
            help=("When true the client will skip the certificate name check."),
        )

        self.mqtt.add_argument(
            "--mqtt_reconnect_delay",
            default=os.environ.get("WM_SERVICES_MQTT_RECONNECT_DELAY", 0),
            action="store",
            type=self.str2int,
            help=(
                "Delay in seconds to try to reconnect when connection to"
                "broker is lost (0 to try forever)"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_max_inflight_messages",
            default=os.environ.get("WM_SERVICES_MQTT_MAX_INFLIGHT_MESSAGES", 20),
            action="store",
            type=self.str2int,
            help=("Max inflight messages for messages with qos > 0"),
        )

        self.mqtt.add_argument(
            "--mqtt_use_websocket",
            default=os.environ.get("WM_SERVICES_MQTT_USE_WEBSOCKET", False),
            type=self.str2bool,
            nargs="?",
            const=True,
            help=(
                "When true the mqtt client will use websocket instead of TCP for transport"
            ),
        )

    def add_buffering_settings(self):
        """ Parameters used to avoid black hole case """
        self.buffering.add_argument(
            "--buffering_max_buffered_packets",
            default=os.environ.get("WM_GW_BUFFERING_MAX_BUFFERED_PACKETS", 0),
            action="store",
            type=self.str2int,
            help=(
                "Maximum number of messages to buffer before "
                "rising sink cost (0 will disable feature)"
            ),
        )

        self.buffering.add_argument(
            "--buffering_max_delay_without_publish",
            default=os.environ.get("WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH", 0),
            action="store",
            type=self.str2int,
            help=(
                "Maximum time to wait in seconds without any "
                "successful publish with packet queued "
                "before rising sink cost (0 will disable feature)"
            ),
        )

        # This minimal sink cost could be moved somewhere as it can be used even
        # buffering limitation is not in use
        self.buffering.add_argument(
            "--buffering_minimal_sink_cost",
            default=os.environ.get("WM_GW_BUFFERING_MINIMAL_SINK_COST", 0),
            action="store",
            type=self.str2int,
            help=(
                "Minimal sink cost for a sink on this gateway. "
                "Can be used to minimize traffic on a gateway, but "
                "it will reduce maximum number of hops for this gateway"
            ),
        )

    def add_debug_settings(self):
        self.debug.add_argument(
            "--debug_incr_data_event_id",
            default=os.environ.get("WM_SERVICES_DEBUG_INCR_EVENT_ID", False),
            type=self.str2bool,
            nargs="?",
            const=True,
            help=(
                "When true the data received event id will be incremental "
                "starting at 0 when service starts. Otherwise it will be "
                "random 64 bits id."
            ),
        )

    @staticmethod
    def _deprecated_message(new_arg_name, deprecated_from="2.x"):
        """ Alerts the user that an argument will be deprecated within the
        next release version
        """
        msg = (
            "Deprecated argument (it will be dropped "
            "from version {} onwards) please use --{} instead."
        ).format(deprecated_from, new_arg_name)
        return msg

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
            type=self.str2int,
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
            type=str,
            help=ParserHelper._deprecated_message("mqtt_certfile"),
        )

        self.deprecated.add_argument(
            "-ua",
            "--unsecure_authentication",
            default=False,
            type=self.str2bool,
            nargs="?",
            const=True,
            help=ParserHelper._deprecated_message("mqtt_force_unsecure"),
        )

        self.deprecated.add_argument(
            "-i",
            "--gwid",
            default=None,
            type=self.str2none,
            help=ParserHelper._deprecated_message("gateway_id"),
        )

    def add_gateway_config(self):
        self.gateway.add_argument(
            "--gateway_id",
            default=os.environ.get("WM_GW_ID", None),
            type=self.str2none,
            help=("Id of the gateway. It must be unique on same broker."),
        )

        self.gateway.add_argument(
            "-fp",
            "--full_python",
            default=False,
            type=self.str2bool,
            nargs="?",
            const=True,
            help=("Do not use C extension for optimization."),
        )

        self.gateway.add_argument(
            "-gm",
            "--gateway_model",
            type=self.str2none,
            default=os.environ.get("WM_GW_MODEL", None),
            help=("Model name of the gateway."),
        )

        self.gateway.add_argument(
            "-gv",
            "--gateway_version",
            type=self.str2none,
            default=os.environ.get("WM_GW_VERSION", None),
            help=("Version of the gateway."),
        )

    def add_filtering_config(self):
        self.filtering.add_argument(
            "-iepf",
            "--ignored_endpoints_filter",
            type=self.str2none,
            default=os.environ.get("WM_GW_IGNORED_ENDPOINTS_FILTER", None),
            help=("Destination endpoints list to ignore (not published)."),
        )

        self.filtering.add_argument(
            "-wepf",
            "--whitened_endpoints_filter",
            type=self.str2none,
            default=os.environ.get("WM_GW_WHITENED_ENDPOINTS_FILTER", None),
            help=(
                "Destination endpoints list to whiten "
                "(no payload content, only size)."
            ),
        )

    def dump(self, path):
        """ dumps the arguments into a file """
        with open(path, "w") as f:
            f.write(serialize(vars(self._arguments)))
