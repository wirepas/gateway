#!/usr/bin/env python3
# Copyright 2020 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
import binascii
import argparse
import os

from enum import Enum

from wirepas_gateway.dbus.dbus_client import BusClient


class NodeRole:
    """Utility class to package a node role

    Helper to manipulate and convert node role based on a Base role
    and a list of flags

    """

    class BaseRole(Enum):
        SINK = 0x1
        ROUTER = 0x2
        NON_ROUTER = 0x3

    class RoleFlags(Enum):
        CSMA_CA = 0x1
        AUTOROLE = 0x8

    def __init__(self, base, flags):
        """Base role constructor

        Args:
            base: a BaseRole
            flags: list of RoleFlags
        """
        self.base = base
        self.flags = flags

    @classmethod
    def from_string(cls, node_role_str):
        """Create a NodeRole from a string

        Args:
            node_role_str: string containing the node role

        Returns: A NodeRole object
        """
        str_lower = node_role_str.lower()
        if "sink" in str_lower:
            base = cls.BaseRole.SINK
        elif "non-router" in str_lower:
            base = cls.BaseRole.NON_ROUTER
        elif "router" in str_lower:
            base = cls.BaseRole.ROUTER
        else:
            raise ValueError("Cannot determine base role from %s" % node_role_str)

        flags = []
        if "csma-ca" in str_lower:
            flags.append(cls.RoleFlags.CSMA_CA)

        if "autorole" in str_lower:
            flags.append(cls.RoleFlags.AUTOROLE)

        return cls(base, flags)

    @classmethod
    def from_dualmcu_value(cls, val):
        """Create a NodeRole from a dualmcu value

        Args:
            val: node role as a 1 byte value from dual mcu api

        Returns: A NodeRole object
        """
        base_int = val & 0x0F
        flags_int = val & 0xF0

        # Define base role
        if base_int == 1:
            base = cls.BaseRole.SINK
        elif base_int == 2:
            base = cls.BaseRole.ROUTER
        elif base_int == 3:
            base = cls.BaseRole.NON_ROUTER

        # Define flags
        flags = []
        if flags_int & 0x10 != 0:
            flags.append(cls.RoleFlags.CSMA_CA)

        if flags_int & 0x80 != 0:
            flags.append(cls.RoleFlags.AUTOROLE)

        return cls(base, flags)

    def to_dualmcu_value(self):
        """Convert node role to dual mcu api value

        Returns: dualmcu value for this role
        """
        val = 0
        if self.base == self.BaseRole.SINK:
            val += 1
        elif self.base == self.BaseRole.ROUTER:
            val += 2
        elif self.base == self.BaseRole.NON_ROUTER:
            val += 3

        if self.RoleFlags.CSMA_CA in self.flags:
            val += 0x10

        if self.RoleFlags.AUTOROLE in self.flags:
            val += 0x80

        return val

    def __str__(self):
        flag_str = ""
        for flag in self.flags:
            flag_str += str(flag.name)
            flag_str += " "

        return "%s, %s" % (self.base.name, flag_str)


class SinkConfigurator(BusClient):
    """Simple class to configure a node

    Use the Dbus api to set or read nodes configuration
    """

    def configure(
        self,
        sink_name,
        node_address=None,
        node_role=None,
        network_address=None,
        network_channel=None,
        start=None,
        authentication_key=None,
        cipher_key=None,
    ):
        sink = self.sink_manager.get_sink(sink_name)
        if sink is None:
            print("Cannot retrieve sink object with name %s" % sink_name)
            return

        # Do the actual configuration
        config = {}
        if node_address is not None:
            config["node_address"] = node_address
        if node_role is not None:
            config["node_role"] = node_role.to_dualmcu_value()
        if network_address is not None:
            config["network_address"] = network_address
        if network_channel is not None:
            config["network_channel"] = network_channel
        if start is not None:
            config["started"] = start
        if cipher_key is not None:
            config["cipher_key"] = cipher_key
        if authentication_key is not None:
            config["authentication_key"] = authentication_key

        ret = sink.write_config(config)
        print("Configuration done with result = {}".format(ret))

    def list_sinks(self):
        sinks = self.sink_manager.get_sinks()

        print("List of sinks:")
        for sink in sinks:
            print("============== [%s] ===============" % sink.sink_id)
            config = sink.read_config()
            for key in config.keys():
                if key == "node_role":
                    print("[%s]: %s" % (key, NodeRole.from_dualmcu_value(config[key])))
                elif key == "app_config_data":
                    print("[%s]: %s" % (key, binascii.hexlify(config[key])))
                else:
                    print("[%s]: %s" % (key, config[key]))
            print("===================================")


def key_type(param_str):
    """Ensure key type conversion

    Args:
        param_str: the key value as a string given by user

    Returns: The key as a bytearray object
    """
    key_str = param_str.replace(",", " ")
    key = bytearray.fromhex(key_str)

    if len(key) != 16:
        raise argparse.ArgumentTypeError("Key is not 128 bits long")

    return key


def node_role_type(param_str):
    """Ensure node role conversion

    Args:
        param_str: the parameter value as a string given by user

    Returns: The role as a NodeRole object
    """
    try:
        return NodeRole.from_string(param_str)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def bool_type(param_str):
    """Ensures string to bool conversion

    Args:
        param_str: the parameter value as a string given by user

    Returns: The value as a boolean
    """
    if param_str.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif param_str.lower() in ("no", "false", "f", "n", "0", ""):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def int_type(param_str):
    """ Ensures string to int conversion to accept 0x format

    Args:
        param_str: the parameter value as a string given by user

    Returns: The value as a boolean
    """
    try:
        value = int(param_str, 0)
    except ValueError:
        raise argparse.ArgumentTypeError("Integer value expected.")
    return value


def get_default_value_from_env(env_var_name):
    value = os.environ.get(env_var_name, None)
    if value is not None and value == "":
        return None
    else:
        return value


def main():
    """Main service to configure a node locally on the gateway

    This tool allows to interact locally on the gateway to configure a node
    with dbus api
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["list", "set"])

    parser.add_argument(
        "-s",
        "--sink_name",
        type=str,
        default=get_default_value_from_env("WM_CN_SINK_ID"),
        help="Sink name as configured in sinkService. Ex: -s sink0",
    )

    parser.add_argument(
        "-n",
        "--node_address",
        type=int_type,
        default=get_default_value_from_env("WM_CN_NODE_ADDRESS"),
        help="Node address as an int. Ex: -n 0xABC or -n 123",
    )

    parser.add_argument(
        "-r",
        "--node_role",
        type=node_role_type,
        default=get_default_value_from_env("WM_CN_NODE_ROLE"),
        help="Node role as a string being any combination of a base role "
        "sink/router/non-router and list of flags from [csma-ca, autorole]."
        'Ex: -r "sink csma-ca" or -r "router csma-ca autorole"',
    )

    parser.add_argument(
        "-N",
        "--network_address",
        type=int_type,
        default=get_default_value_from_env("WM_CN_NETWORK_ADDRESS"),
        help="Network address as an int. Ex: -N 0xA1B2C3 or -N 123456",
    )

    parser.add_argument(
        "-c",
        "--network_channel",
        type=int_type,
        default=get_default_value_from_env("WM_CN_NETWORK_CHANNEL"),
        help="Network channel as an int. Ex: -c 5",
    )

    parser.add_argument(
        "-ak",
        "--authentication_key",
        type=key_type,
        default=get_default_value_from_env("WM_CN_AUTHENTICATION_KEY"),
        help="Network wide 128 bytes authentication key. "
        "Ex: -ak 112233445566778899AABBCCDDEEFF11 "
        "or -ak 11,22,33,44,55,66,77,88,99,AA,BB,CC,DD,EE,FF,11",
    )

    parser.add_argument(
        "-ck",
        "--cipher_key",
        type=key_type,
        default=get_default_value_from_env("WM_CN_CIPHER_KEY"),
        help="Network wide cipher key. "
        "Ex: -ck 112233445566778899AABBCCDDEEFF11 "
        "or -ck 11,22,33,44,55,66,77,88,99,AA,BB,CC,DD,EE,FF,11",
    )

    parser.add_argument(
        "-S",
        "--start",
        type=bool_type,
        default=get_default_value_from_env("WM_CN_START_SINK"),
        help="Start the sink after configuration",
    )

    args = parser.parse_args()

    sink_configurator = SinkConfigurator()

    if args.cmd == "list":
        sink_configurator.list_sinks()

    if args.cmd == "set":
        sink_configurator.configure(
            node_address=args.node_address,
            node_role=args.node_role,
            network_address=args.network_address,
            network_channel=args.network_channel,
            sink_name=args.sink_name,
            start=args.start,
            authentication_key=args.authentication_key,
            cipher_key=args.cipher_key,
        )


if __name__ == "__main__":
    main()
