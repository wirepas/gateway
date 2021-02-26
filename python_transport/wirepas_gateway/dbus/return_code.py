# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import re
from wirepas_mesh_messaging import GatewayResultCode


class ReturnCode:
    """
    Class that represent all possible error and facility function to create error
    """

    # Conversion from c_mesh_lib (dbus) error codes
    # Some error codes can only happen if implementation is wrong in gateway
    errors_from_c_mesh_lib_code = dict(
        [
            # APP_RES_OK, Everything is ok
            (0, GatewayResultCode.GW_RES_OK),
            # APP_RES_STACK_NOT_STOPPED, Stack is not stopped
            (1, GatewayResultCode.GW_RES_INVALID_SINK_STATE),
            # APP_RES_STACK_ALREADY_STOPPED, Stack is already stopped
            (2, GatewayResultCode.GW_RES_INVALID_SINK_STATE),
            # APP_RES_STACK_ALREADY_STARTED, Stack is already started
            (3, GatewayResultCode.GW_RES_INVALID_SINK_STATE),
            # APP_RES_INVALID_VALUE, A parameter has an invalid value
            (4, GatewayResultCode.GW_RES_INVALID_PARAM),
            # APP_RES_ROLE_NOT_SET, The node role is not set
            (5, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_NODE_ADD_NOT_SET, The node address is not set
            (6, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_NET_ADD_NOT_SET, The network address is not set
            (7, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_NET_CHAN_NOT_SET, The network channel is not set
            (8, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_STACK_IS_STOPPED, Stack is stopped
            (9, GatewayResultCode.GW_RES_INVALID_SINK_STATE),
            # APP_RES_NODE_NOT_A_SINK, Node is not a sink
            (10, GatewayResultCode.GW_RES_INVALID_ROLE),
            # APP_RES_UNKNOWN_DEST, Unknown destination address
            (11, GatewayResultCode.GW_RES_INVALID_DEST_ADDRESS),
            # APP_RES_NO_CONFIG, No configuration received/set
            (12, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_ALREADY_REGISTERED, Cannot register several times
            (13, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_NOT_REGISTERED, Cannot unregister if not registered first
            (14, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_ATTRIBUTE_NOT_SET, Attribute is not set yet
            (15, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_ACCESS_DENIED, Access denied
            (16, GatewayResultCode.GW_RES_ACCESS_DENIED),
            # APP_RES_DATA_ERROR, Error in data
            (17, GatewayResultCode.GW_RES_INVALID_DATA_PAYLOAD),
            # APP_RES_NO_SCRATCHPAD_START, No scratchpad start request sent
            (18, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_NO_VALID_SCRATCHPAD, No valid scratchpad
            (19, GatewayResultCode.GW_RES_NO_SCRATCHPAD_PRESENT),
            # APP_RES_NOT_A_SINK, Stack is not a sink
            (20, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_OUT_OF_MEMORY, Out of memory
            # TODO Change error code to GW_RES_SINK_OUT_OF_MEMORY in next release
            (21, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_INVALID_DIAG_INTERVAL, Invalid diag interval
            (22, GatewayResultCode.GW_RES_INVALID_DIAG_INTERVAL),
            # APP_RES_INVALID_SEQ,  Invalid sequence number
            (23, GatewayResultCode.GW_RES_INVALID_SEQUENCE_NUMBER),
            # APP_RES_INVALID_START_ADDRESS, Start address is invalid
            (24, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_INVALID_NUMBER_OF_BYTES, Invalid number of bytes
            (25, GatewayResultCode.GW_RES_INTERNAL_ERROR),
            # APP_RES_INVALID_SCRATCHPAD, Scratchpad is not valid
            (26, GatewayResultCode.GW_RES_INVALID_SCRATCHPAD),
            # APP_RES_INVALID_REBOOT_DELAY, Invalid reboot delay
            (27, GatewayResultCode.GW_RES_INVALID_REBOOT_DELAY),
            # APP_RES_INTERNAL_ERROR, WPC internal error
            (28, GatewayResultCode.GW_RES_INTERNAL_ERROR),
        ]
    )

    @staticmethod
    def error_from_dbus_exception(exception_message):
        # Parse the error
        m = re.search(
            r"\[([a-zA-Z0-9_]+)\]: C Mesh Lib ret = ([0-9]+)", exception_message
        )
        if m:
            # The function name could help to give a better Result code
            # APP_RES_INVALID_VALUE is returned by multiple lib calls
            # and it can be for example GW_RES_INVALID_NETWORK_ADDRESS or
            # GW_RES_INVALID_NETWORK_ADDRESS depending of function name
            # for now it is always GW_RES_INVALID_PARAM
            return ReturnCode.error_from_dbus_return_code(int(m.group(2)))

        return GatewayResultCode.GW_RES_INTERNAL_ERROR

    @staticmethod
    def error_from_dbus_return_code(ret_code):
        try:
            error = ReturnCode.errors_from_c_mesh_lib_code[ret_code]
        except KeyError:
            error = GatewayResultCode.GW_RES_INTERNAL_ERROR
        return error
