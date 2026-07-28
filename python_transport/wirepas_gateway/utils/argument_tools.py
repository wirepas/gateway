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
import textwrap
import shutil
from enum import Enum

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


class BufferingAction(Enum):
    RAISE_SINK_COST = "raise_sink_cost"
    STOP_STACK = "stop_stack"
    DROP_PACKETS = "drop_packets"

    def __str__(self):
        return self.value


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
        description=None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        version=None,
    ):
        super(ParserHelper, self).__init__()
        self._parser = argparse.ArgumentParser(formatter_class=formatter_class)
        if description is not None:
            self.add_wrapped_description(self._parser, description)

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
        """ Converts empty strings to None """
        if value == "":
            return None
        return value

    def add_env_argument(self,
                         group,
                         env_variable,
                         *args,
                         **kwargs):
        """
        Wrapper for adding an argument which can be set with an environment
        variable. Arbitrary arguments are passed to argparse.
        """
        default = kwargs.get("default")
        kwargs["default"] = os.environ.get(env_variable, default)

        help_text = []
        if "help" in kwargs:
            help_text.append(kwargs["help"])
        if "choices" in kwargs:
            choice_strs = [str(choice) for choice in kwargs["choices"]]
            result = '[%s]' % ', '.join(choice_strs)
            help_text.append(f"(choices: {result})")
        help_text.append(f"(default: {default})")

        kwargs["help"] = " ".join(help_text)
        kwargs["metavar"] = "$" + env_variable
        group.add_argument(*args, **kwargs)

    def add_wrapped_description(self, target, description, indentation = 2):
        """
        Wraps the given description to fit the terminal while keeping line
        beaks and adds it to the given target (for example argument group).
        """
        width = shutil.get_terminal_size().columns - indentation
        lines = []
        for paragraph in description.splitlines():
            if not paragraph:
                lines.append("")
                continue
            wrapped = textwrap.wrap(paragraph, width, replace_whitespace=False)
            lines.extend(wrapped)

        target.description = "\n".join(lines)

    def add_file_settings(self):
        """ For file setting handling"""
        self.add_env_argument(
            self.file_settings,
            "WM_GW_FILE_SETTINGS",
            "--settings",
            type=self.str2none,
            required=False,
            default=None,
            help="A yaml file with argument parameters (see help for options).",
        )

    def add_mqtt(self):
        """ Commonly used MQTT arguments """
        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_HOSTNAME",
            "--mqtt_hostname",
            default=None,
            action="store",
            type=self.str2none,
            help="MQTT broker hostname.",
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_USERNAME",
            "--mqtt_username",
            default=None,
            action="store",
            type=self.str2none,
            help="MQTT broker username.",
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_PASSWORD",
            "--mqtt_password",
            default=None,
            action="store",
            type=self.str2none,
            help="MQTT broker password.",
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_PORT",
            "--mqtt_port",
            default=8883,
            action="store",
            type=self.str2int,
            help="MQTT broker port.",
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_CA_CERTS",
            "--mqtt_ca_certs",
            default=None,
            action="store",
            type=self.str2none,
            help=(
                "Path to the Certificate "
                "Authority certificate files that "
                "are to be treated as trusted by "
                "this client."
            ),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_CLIENT_CRT",
            "--mqtt_certfile",
            default=None,
            action="store",
            type=self.str2none,
            help=("Path to the PEM encoded client certificate."),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_CLIENT_KEY",
            "--mqtt_keyfile",
            default=None,
            action="store",
            type=self.str2none,
            help=("Path to the PEM encoded client private key."),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_CERT_REQS",
            "--mqtt_cert_reqs",
            default="CERT_REQUIRED",
            choices=["CERT_REQUIRED", "CERT_OPTIONAL", "CERT_NONE"],
            action="store",
            type=self.str2none,
            help=(
                "Defines the certificate "
                "requirements that the client "
                "imposes on the broker."
            ),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_TLS_VERSION",
            "--mqtt_tls_version",
            default="PROTOCOL_TLSv1_2",
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

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_CIPHERS",
            "--mqtt_ciphers",
            default=None,
            action="store",
            type=self.str2none,
            help=(
                "A string specifying which "
                "encryption ciphers are allowable "
                "for this connection."
            ),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_PERSIST_SESSION",
            "--mqtt_persist_session",
            default=False,
            type=self.str2bool,
            nargs="?",
            const=True,
            help=(
                "When True the broker will buffer session packets "
                "between reconnection."
            ),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_FORCE_UNSECURE",
            "--mqtt_force_unsecure",
            default=False,
            type=self.str2bool,
            nargs="?",
            const=True,
            help=("When true, connect to the broker without TLS."),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_RECONNECT_DELAY",
            "--mqtt_reconnect_delay",
            default=0,
            action="store",
            type=self.str2int,
            help=(
                "Time in seconds to keep trying to reconnect when the "
                "connection to the broker is lost. If it expires, the "
                "service exits. 0 to retry forever."
            ),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_MAX_INFLIGHT_MESSAGES",
            "--mqtt_max_inflight_messages",
            default=20,
            action="store",
            type=self.str2int,
            help=("Max inflight messages for messages with qos > 0"),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_USE_WEBSOCKET",
            "--mqtt_use_websocket",
            default=False,
            type=self.str2bool,
            nargs="?",
            const=True,
            help=(
                "When true the mqtt client will use websocket instead of TCP for transport"
            ),
        )

        self.add_env_argument(
            self.mqtt,
            "WM_SERVICES_MQTT_RATE_LIMIT_PPS",
            "--mqtt_rate_limit_pps",
            default=0,
            action="store",
            type=self.str2int,
            help=(
                "Max rate limit for the mqtt client to publish on mqtt broker. It can be set to "
                "protect the broker from very high usage when one or more gateways are offline for a while "
                "and publish all their buffers when connection to broker is restored. "
                "0 to disable the limit."
            ),
        )

    def add_buffering_settings(self):
        """ Parameters used to avoid black hole case """
        self.add_wrapped_description(
            self.buffering,
            textwrap.dedent("""\
            If the MQTT connection is lost, transport service might end up
            buffering uplink packets and never send them to the MQTT broker,
            becoming a "black hole".

            Transport service can be configured to detect this and avoid it in
            different ways, which can be selected by WM_GW_BUFFERING_ACTION
            parameter. By default, transport service will buffer outgoing MQTT
            messages without any limit and retry connecting to the broker.

            The black hole prevention can be enabled by setting
            WM_GW_BUFFERING_MAX_BUFFERED_PACKETS or
            WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH parameter.

            Different actions are described below:

            * 'raise_sink_cost'
              Sink costs of sinks connected to this gateway are raised to
              discourage nodes from connecting to sinks under this gateway.

            * 'stop_stack'
              Sinks connected to this gateway are stopped to ensure nodes are
              not connected to sinks under this gateway.

            * 'drop_packets'
              Enabled only by WM_GW_BUFFERING_MAX_BUFFERED_PACKETS;
              WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH cannot be used with
              this action. Internal publish queue size is limited to
              WM_GW_BUFFERING_MAX_BUFFERED_PACKETS and the oldest MQTT messages
              are dropped if necessary. Drops are reported in the log
              periodically.

            Once the MQTT connection is reestablished, the transport service
            waits until all buffered messages have been successfully published
            before lowering sink costs or starting sinks again. This is done to
            prevent modifying sink parameters in unstable connections with
            intermittent disconnects. Also see the WM_SERVICES_MQTT_RATE_LIMIT_PPS
            parameter.

            When lowering sink costs, the value of
            WM_GW_BUFFERING_MINIMAL_SINK_COST is used. It is also applied to
            sinks at startup, even when black hole prevention is disabled:
            unlike most sink configuration parameters, sink cost cannot be set
            over the MQTT interface, so a raised cost left behind by an earlier
            gateway configuration could not be lowered by the backend
            otherwise.
            """),
        )

        self.add_env_argument(
            self.buffering,
            "WM_GW_BUFFERING_MAX_BUFFERED_PACKETS",
            "--buffering_max_buffered_packets",
            default=0,
            action="store",
            type=self.str2int,
            help=(
                "Maximum number of messages to buffer before "
                "taking an action. 0 will disable feature"
            ),
        )

        self.add_env_argument(
            self.buffering,
            "WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH",
            "--buffering_max_delay_without_publish",
            default=0,
            action="store",
            type=self.str2int,
            help=(
                "Maximum time to wait in seconds without any "
                "successful publish with packet queued "
                "before taking an action. 0 will disable feature"
            ),
        )

        self.add_env_argument(
            self.buffering,
            "WM_GW_BUFFERING_ACTION",
            "--buffering_action",
            default=None,
            type=BufferingAction,
            choices=list(BufferingAction),
            help=("Action to take when the buffer limit is reached. "
                  "When empty, it is assumed to be 'raise_sink_cost'."
            ),
        )

        # This minimal sink cost could be moved somewhere as it can be used even
        # buffering limitation is not in use
        self.add_env_argument(
            self.buffering,
            "WM_GW_BUFFERING_MINIMAL_SINK_COST",
            "--buffering_minimal_sink_cost",
            default=0,
            action="store",
            type=self.str2int,
            help=(
                "Minimal sink cost for a sink on this gateway. "
                "Can be used to minimize traffic on a gateway, but "
                "it will reduce maximum number of hops for this gateway"
            ),
        )

    def add_debug_settings(self):
        self.add_env_argument(
            self.debug,
            "WM_DEBUG_LEVEL",
            "--log_level",
            default="info",
            type=str,
            choices=["debug", "info", "warning", "error", "critical"],
            help=(
                "Log level of the transport service. 'debug' level might "
                "generate too much logs and is not recommended to be used in a "
                "production system."
            ),
        )

        self.add_env_argument(
            self.debug,
            "WM_SERVICES_DEBUG_INCR_EVENT_ID",
            "--debug_incr_data_event_id",
            default=False,
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
    def _deprecated_message(new_arg_name="", deprecated_from="2.x"):
        """ Alerts the user that an argument will be deprecated within the
        next release version
        """
        msg = (
            "Deprecated argument (it will be dropped "
            f"from version {deprecated_from} onwards)"
        )
        if new_arg_name:
            msg += f" please use --{new_arg_name} instead."
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

        self.add_env_argument(
            self.deprecated,
            "WM_SERVICES_MQTT_ALLOW_UNTRUSTED",
            "--mqtt_allow_untrusted",
            default=False,
            type=self.str2bool,
            nargs="?",
            const=True,
            help="Not in use. " + ParserHelper._deprecated_message(),
        )

        self.add_env_argument(
            self.deprecated,
            "WM_GW_BUFFERING_STOP_STACK",
            "--buffering_stop_stack",
            default=None,
            type=self.str2bool,
            help=ParserHelper._deprecated_message("buffering_action"),
        )

    def add_gateway_config(self):
        self.add_env_argument(
            self.gateway,
            "WM_GW_ID",
            "--gateway_id",
            default=None,
            type=self.str2none,
            help=(
                "Id of the gateway. It must be unique on same broker. "
                "When empty, an id is generated based on the network "
                "interface MAC address (uuid.getnode()). The id is used "
                "in MQTT topics without escaping, so special MQTT "
                "characters (+, #, /) should be avoided."
            ),
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

        self.add_env_argument(
            self.gateway,
            "WM_GW_MODEL",
            "-gm",
            "--gateway_model",
            type=self.str2none,
            default=None,
            help=("Model name of the gateway."),
        )

        self.add_env_argument(
            self.gateway,
            "WM_GW_VERSION",
            "-gv",
            "--gateway_version",
            type=self.str2none,
            default=None,
            help=("Version of the gateway."),
        )

        self.add_env_argument(
            self.gateway,
            "WM_GW_MAX_SCRAT_SIZE",
            "-gmss",
            "--gateway_max_scratchpad_size",
            type=self.str2int,
            default=None,
            help=("Maximum scratchpad size a gateway can accept. If scratchpad is bigger "
                  "it must be sent as chunks smaller or equal to this value"),
        )

    def add_filtering_config(self):
        self.add_wrapped_description(
            self.filtering,
            textwrap.dedent("""\
            Filters to limit which packets received from the Wirepas
            network are published to the MQTT broker. Both filters apply
            to uplink traffic only and select packets based on their
            destination endpoint. Downlink traffic is never filtered.

            Both parameters accept a list of endpoints (i.e. [1,2,3]), a
            range of endpoints (i.e. [1-3]), or a combination of both
            (i.e. [1,2,10-15]). Valid endpoint values are 0-255. An
            endpoint cannot be in both lists at the same time.
            """),
        )

        self.add_env_argument(
            self.filtering,
            "WM_GW_IGNORED_ENDPOINTS_FILTER",
            "-iepf",
            "--ignored_endpoints_filter",
            type=self.str2none,
            default=None,
            help=(
                "Destination endpoints list to ignore. Packets sent to "
                "these endpoints are not published at all."
            ),
        )

        self.add_env_argument(
            self.filtering,
            "WM_GW_WHITENED_ENDPOINTS_FILTER",
            "-wepf",
            "--whitened_endpoints_filter",
            type=self.str2none,
            default=None,
            help=(
                "Destination endpoints list to whiten (i.e. blank out the "
                "payload). Packets sent to these endpoints are published "
                "without the payload content, only the payload size is kept."
            ),
        )

    def dump(self, path):
        """ dumps the arguments into a file """
        with open(path, "w") as f:
            f.write(serialize(vars(self._arguments)))
