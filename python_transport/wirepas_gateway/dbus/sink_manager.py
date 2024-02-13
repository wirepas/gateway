# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import logging
import wirepas_mesh_messaging as wmm

from gi.repository import GLib
from .return_code import ReturnCode


DBUS_SINK_PREFIX = "com.wirepas.sink."


class Sink:
    def __init__(self, bus, proxy, sink_id, unique_name, on_stack_started, on_stack_stopped):

        self.proxy = proxy
        self.sink_id = sink_id
        self.network_address = None
        self.on_stack_started = on_stack_started
        self.on_stack_stopped = on_stack_stopped
        self.bus = bus
        self.unique_name = unique_name
        self._on_started_handle = None
        self._on_stopped_handle = None
        self._last_config_dict = None

    def register_for_stack_started(self):
        # Use the subscribe directly to be able to specify the sender
        self._on_started_handle = self.bus.subscribe(
            signal="StackStarted",
            object="/com/wirepas/sink",
            iface="com.wirepas.sink.config1",
            sender=self.unique_name,
            signal_fired=self._on_stack_started,
        )

    def unregister_from_stack_started(self):
        if self._on_started_handle is not None:
            self._on_started_handle.unsubscribe()

    def register_for_stack_stopped(self):
        # Use the subscribe directly to be able to specify the sender
        self._on_stopped_handle = self.bus.subscribe(
            signal="StackStopped",
            object="/com/wirepas/sink",
            iface="com.wirepas.sink.config1",
            sender=self.unique_name,
            signal_fired=self._on_stack_stopped,
        )

    def unregister_from_stack_stopped(self):
        if self._on_stopped_handle is not None:
            self._on_stopped_handle.unsubscribe()

    def get_network_address(self, force=False):
        if self.network_address is None or force:
            # Network address is not known or must be updated
            try:
                self.network_address = self.proxy.NetworkAddress
            except GLib.Error:
                logging.error("Could not get network address")

        return self.network_address

    def send_data(
        self,
        dst,
        src_ep,
        dst_ep,
        qos,
        initial_time,
        data,
        is_unack_csma_ca=False,
        hop_limit=0,
    ):
        try:
            res = self.proxy.SendMessage(
                # For some reason on some arch, uint32 are not correctly handled
                dst & 0xFFFFFFFF,
                src_ep,
                dst_ep,
                initial_time,
                qos,
                is_unack_csma_ca,
                hop_limit,
                data,
            )
            if res != 0:
                logging.error("Cannot send message err=%s", res)
                return ReturnCode.error_from_dbus_return_code(res)
        except GLib.Error as e:
            logging.error("Fail to send message: %s", str(e))
            return ReturnCode.error_from_dbus_exception(str(e))
        except OverflowError:
            # It may happens as protobuf has bigger container value
            logging.error("Invalid range value")
            return wmm.GatewayResultCode.GW_RES_INVALID_PARAM

        return wmm.GatewayResultCode.GW_RES_OK

    def _on_stack_started(self, sender, object, iface, signal, params):
        # pylint: disable=unused-argument
        # pylint: disable=redefined-builtin
        # Force update of network address in case remote api modify it
        self.get_network_address(True)

        self.on_stack_started(self.sink_id)

    def _on_stack_stopped(self, sender, object, iface, signal, params):
        self.on_stack_stopped(self.sink_id)

    def _get_param(self, dic, key, attribute):
        try:
            dic[key] = getattr(self.proxy, attribute)
        except  GLib.Error:
            if key != "channel_map":
                # Warning and not an error as normal behavior if not set
                logging.warning("Cannot get %s in config (is it set?)", key)

        except AttributeError :
            logging.warning("Attribute %s doesn't exist", key)

    def _get_pair_params(self, dic, key1, att1, key2, att2):
        # Some settings are only relevant if the both can be retrieved
        try:
            att1_val = getattr(self.proxy, att1)
            att2_val = getattr(self.proxy, att2)
        except GLib.Error:
            logging.debug("Cannot get one of the pair value (%s-%s)", key1, key2)
            return

        dic[key1] = att1_val
        dic[key2] = att2_val

    def read_config(self):
        config = {}
        config["sink_id"] = self.sink_id
        partial = False

        # Should always be available
        try:
            config["started"] = (self.proxy.StackStatus & 0x01) == 0
        except GLib.Error as e:
            error = ReturnCode.error_from_dbus_exception(str(e))
            logging.error("Cannot get Stack state: %s", error)

        self._get_param(config, "node_address", "NodeAddress")
        self._get_param(config, "node_role", "NodeRole")
        self._get_param(config, "network_address", "NetworkAddress")
        self._get_param(config, "network_channel", "NetworkChannel")
        self._get_param(config, "channel_map", "ChannelMap")
        self._get_pair_params(config, "max_ac", "ACRangeMax", "min_ac", "ACRangeMin")
        self._get_pair_params(
            config, "max_ac_cur", "ACRangeMaxCur", "min_ac_cur", "ACRangeMinCur"
        )
        self._get_pair_params(config, "max_ch", "ChRangeMax", "min_ch", "ChRangeMin")
        self._get_param(config, "max_mtu", "MaxMtu")
        self._get_param(config, "hw_magic", "HwMagic")
        self._get_param(config, "stack_profile", "StackProfile")
        self._get_param(config, "firmware_version", "FirmwareVersion")
        self._get_param(config, "app_config_max_size", "AppConfigMaxSize")

        try:
            are_keys_set = self.proxy.AuthenticationKeySet and self.proxy.CipherKeySet

            config["are_keys_set"] = are_keys_set
        except GLib.Error:
            logging.error("Cannot get key status")

        try:
            seq, diag, data = self.proxy.GetAppConfig()
            config["app_config_seq"] = seq
            config["app_config_diag"] = diag
            config["app_config_data"] = bytearray(data)
        except GLib.Error:
            # If node is blank it is not a sink
            # so app config cannot be accessed
            logging.warning("Cannot get App Config")

        # Add scratchpad related info
        self.get_scratchpad_status(config)

        if self._last_config_dict is not None:
            for key, value in self._last_config_dict.items():
                if key not in config:
                    logging.warning("Add %s from cache in config", key)
                    config[key] = value
                    partial = True

        self._last_config_dict = config.copy()

        return config, partial

    def _set_param(self, dic, key, attribute):
        try:
            value = dic[key]
            # Stop the stack if not already stopped
            if self.proxy.StackStatus == 0:
                self.proxy.SetStackState(False)

            setattr(self.proxy, attribute, value)

        except KeyError:
            # key not defined in config
            logging.debug("key not present: %s", key)
        except GLib.Error as e:
            # Exception raised when setting attribute
            logging.error(
                "Cannot set %s for param %s on sink %s: %s",
                value,
                key,
                self.sink_id,
                str(e),
            )
            return ReturnCode.error_from_dbus_exception(str(e))
        except OverflowError:
            # It may happens as protobuf has bigger container value
            logging.error(
                "Invalid range value for param %s with value %s", key, value
            )
            return wmm.GatewayResultCode.GW_RES_INVALID_PARAM

        return wmm.GatewayResultCode.GW_RES_OK

    def write_config(self, config):
        # Force the node address if used
        try:
            # For some reason on some arch, uint32 are not correctly handled and result to an overflow
            config["node_address"] = config["node_address"] & 0xFFFFFFFF
        except KeyError:
            # Node addess is not in the config
            pass
        # Should always be available
        try:
            stack_started = (self.proxy.StackStatus & 0x01) == 0
        except GLib.Error as e:
            res = ReturnCode.error_from_dbus_exception(str(e))
            logging.error(
                "Cannot get Stack state. Problem in communication probably: %s",
                res.name,
            )
            return res

        # The write config has only one return code possible
        # so the last error code will be returned
        res = wmm.GatewayResultCode.GW_RES_OK

        config_to_dbus_param = dict(
            [
                ("node_address", "NodeAddress"),
                ("node_role", "NodeRole"),
                ("network_address", "NetworkAddress"),
                ("network_channel", "NetworkChannel"),
                ("channel_map", "ChannelMap"),
                ("authentication_key", "AuthenticationKey"),
                ("cipher_key", "CipherKey"),
            ]
        )

        # Any following call will stop the stack
        for param in config_to_dbus_param:
            tmp = self._set_param(config, param, config_to_dbus_param[param])
            if tmp != wmm.GatewayResultCode.GW_RES_OK:
                # Update result code only if not success to avoid erasing
                # previous error (only one return code)
                res = tmp

        # Set app_config after node role config in case role was not sink before
        try:
            seq = config["app_config_seq"]
            diag = config["app_config_diag"]
            data = config["app_config_data"]

            logging.info("Set app config with %s", config)
            self.proxy.SetAppConfig(seq, diag, data)
        except KeyError:
            # App config not defined in new config
            logging.debug("Missing key app_config key in config: %s", config)
        except GLib.Error as e:
            res = ReturnCode.error_from_dbus_exception(str(e))
            logging.error("Cannot set App Config: %s", res.name)
        except OverflowError:
            # It may happens as protobuf has bigger container value
            res = wmm.GatewayResultCode.GW_RES_INVALID_PARAM
            logging.error("Invalid range value")

        # Set stack in state defined by new config or set it as it was
        # previously
        try:
            new_state = config["started"]
        except KeyError:
            # Not defined in config
            new_state = stack_started

        try:
            current_state = (self.proxy.StackStatus & 0x01) == 0
            # Change stack state only if needed to avoid unnecessary events
            if current_state != new_state:
                logging.debug(
                    "Change stack state from %s to %s", current_state, new_state
                )
                self.proxy.SetStackState(new_state)
        except GLib.Error as err:
            res = ReturnCode.error_from_dbus_exception(str(err))
            logging.error(
                "Cannot set Stack state. Problem in communication probably: %s",
                res.name,
            )
            return res

        # In case the network address was updated, read it back for our cached
        # value
        self.get_network_address(True)

        return res

    @property
    def cost(self):
        try:
            cost = self.proxy.SinkCost
        except GLib.Error:
            logging.error("Cannot get sink cost for sink {}".format(self.sink_id))
            cost = 0
        return cost

    @cost.setter
    def cost(self, new_cost):
        if new_cost is None or new_cost < 0 or new_cost > 254:
            raise ValueError("Wrong sink cost value {}".format(new_cost))

        try:
            self.proxy.SinkCost = new_cost
        except GLib.Error as err:
            res = ReturnCode.error_from_dbus_exception(err.message)
            if res == wmm.GatewayResultCode.GW_RES_INVALID_ROLE:
                logging.warning("Node role is not a sink, sink cost cannot be modified")
                raise ValueError("Wrong role to set cost value {}".format(new_cost))
            else:
                logging.error("Cannot set sink cost for sink {} ({})".format(self.sink_id, res))

    def get_scratchpad_status(self, out_d=None):
        if out_d is None:
            d = {}
        else:
            d = out_d

        dbus_to_gateway_satus = dict(
            [
                (0, wmm.ScratchpadStatus.SCRATCHPAD_STATUS_SUCCESS),
                (255, wmm.ScratchpadStatus.SCRATCHPAD_STATUS_NEW)
                # Anything else is ERROR
            ]
        )
        try:
            status = self.proxy.StoredStatus
            d["stored_status"] = dbus_to_gateway_satus[status]
        except GLib.Error:
            # Exception raised when getting attribute (probably not set)
            logging.error("Cannot get stored status in config")
        except KeyError:
            # Between 1 and 254 => Error
            logging.error("Scratchpad stored status has error: %s", status)
            d["stored_status"] = wmm.ScratchpadStatus.SCRATCHPAD_STATUS_ERROR

        dbus_to_gateway_type = dict(
            [
                (0, wmm.ScratchpadType.SCRATCHPAD_TYPE_BLANK),
                (1, wmm.ScratchpadType.SCRATCHPAD_TYPE_PRESENT),
                (2, wmm.ScratchpadType.SCRATCHPAD_TYPE_PROCESS),
            ]
        )
        try:
            stored_type = self.proxy.StoredType
            d["stored_type"] = dbus_to_gateway_type[stored_type]
        except GLib.Error:
            # Exception raised when getting attribute (probably not set)
            logging.error("Cannot get stored type in config\n")

        stored = {}
        self._get_param(stored, "seq", "StoredSeq")
        self._get_param(stored, "crc", "StoredCrc")
        self._get_param(stored, "len", "StoredLen")
        d["stored_scratchpad"] = stored

        processed = {}
        self._get_param(processed, "seq", "ProcessedSeq")
        self._get_param(processed, "crc", "ProcessedCrc")
        self._get_param(processed, "len", "ProcessedLen")
        d["processed_scratchpad"] = processed

        self._get_param(d, "firmware_area_id", "FirmwareAreaId")

        # Read Target only if firmware is greater than 5.1
        stack_version = self.proxy.FirmwareVersion
        if stack_version[0] > 5 or (stack_version[0] == 5 and stack_version[1] > 0):
            # Target scratchpad should be supported (except if dualmcu is too old)
            try:
                seq, crc, action, param = self.proxy.GetTargetScratchpad()
                target_and_action = {}
                target_and_action["action"] = wmm.ScratchpadAction(
                    action + 1
                )  # Plus one as dualmcu version starts at 0, and we start at 1
                target_and_action["target_sequence"] = seq
                target_and_action["target_crc"] = crc
                if target_and_action["action"] == wmm.ScratchpadAction.ACTION_PROPAGATE_AND_PROCESS_WITH_DELAY:
                    # check if delay is in predifined list
                    param_to_delay_dic = {
                        0x4A: wmm.ProcessingDelay.DELAY_TEN_MINUTES,
                        0x5E: wmm.ProcessingDelay.DELAY_THIRTY_MINUTES,
                        0x81: wmm.ProcessingDelay.DELAY_ONE_HOUR,
                        0x86: wmm.ProcessingDelay.DELAY_SIX_HOURS,
                        0xC1: wmm.ProcessingDelay.DELAY_ONE_DAY,
                        0xC2: wmm.ProcessingDelay.DELAY_TWO_DAYS,
                        0xC5: wmm.ProcessingDelay.DELAY_FIVE_DAYS
                    }

                    try:
                        target_and_action["delay"] = param_to_delay_dic[param]
                    except KeyError:
                        logging.debug("Delay not in predifined list: %d", param)
                        target_and_action["param"] = param

                else:
                    target_and_action["param"] = param

                d["target_and_action"] = target_and_action
            except GLib.Error:
                logging.warning("Cannot get Target Scratchpad")

        return d

    def process_scratchpad(self):
        ret = wmm.GatewayResultCode.GW_RES_OK
        restart = False
        try:
            # Stop the stack if not already stopped
            if self.proxy.StackStatus == 0:
                self.proxy.SetStackState(False)
                restart = True
        except GLib.Error:
            logging.error("Sink in invalid state")
            return wmm.GatewayResultCode.GW_RES_INVALID_SINK_STATE

        try:
            self.proxy.ProcessScratchpad()
        except GLib.Error as e:
            ret = ReturnCode.error_from_dbus_exception(str(e))
            logging.error("Could not restore sink's state: %s", ret.name)

        if restart:
            try:
                self.proxy.SetStackState(True)
            except GLib.Error as e:
                ret = ReturnCode.error_from_dbus_exception(str(e))
                logging.debug("Sink in invalid state: %s", ret.name)

        return ret

    def upload_scratchpad(self, seq, file):
        ret = wmm.GatewayResultCode.GW_RES_OK
        restart = False
        try:
            # Stop the stack if not already stopped
            if self.proxy.StackStatus == 0:
                self.proxy.SetStackState(False)
                restart = True
        except GLib.Error:
            logging.error("Sink in invalid state")
            return wmm.GatewayResultCode.GW_RES_INVALID_SINK_STATE

        try:
            self.proxy.UploadScratchpad(seq, file)
            logging.info(
                "Scratchpad loaded with seq %d on sink %s", seq, self.sink_id
            )
        except GLib.Error as e:
            ret = ReturnCode.error_from_dbus_exception(str(e))
            logging.error("Cannot upload local scratchpad: %s", ret.name)
        except OverflowError:
            # It may happens as protobuf has bigger container value
            ret = wmm.GatewayResultCode.GW_RES_INVALID_PARAM
            logging.error("Invalid range value")

        if restart:
            try:
                # Restart sink if we stopped it for this request
                self.proxy.SetStackState(True)
            except GLib.Error as e:
                ret = ReturnCode.error_from_dbus_exception(str(e))
                logging.error("Could not restore sink's state: %s", ret.name)

        return ret

    def set_target_scratchpad(self, action, target_seq, target_crc, param):
        ret = wmm.GatewayResultCode.GW_RES_OK

        if (
            action == wmm.ScratchpadAction.ACTION_NO_OTAP
            or action == wmm.ScratchpadAction.ACTION_LEGACY_OTAP
        ):
            # There is no target with those actions, default to 0
            target_seq = 0
            target_crc = 0
            param = 0
        else:
            # check params in case there is an action with valid target
            try:
                if target_seq is None:
                    # Target seq not specified, take local one
                    target_seq = self.proxy.StoredSeq

                if target_crc is None:
                    # Target crc not specified, take local one
                    target_crc = self.proxy.StoredCrc
            except GLib.Error as e:
                ret = ReturnCode.error_from_dbus_exception(str(e))
                logging.error(
                    "Cannot get local scratchpad info for set_target: %s", ret.name
                )

            if target_seq == 0:
                logging.error("Seq 0 is not a valid target")
                return wmm.GatewayResultCode.GW_RES_INVALID_PARAM

        try:
            # If there is no param for the action, default it to 0 before
            # calling sink service through DBUS
            if param is None:
                param = 0

            logging.info(
                "Scratchpad target set to Action %s (%d) with seq"
                " %d and crc %d on sink %s",
                action,
                param,
                target_seq,
                target_crc,
                self.sink_id,
            )

            # Do a minus 1 as action are shifted by one with dual mcu
            self.proxy.SetTargetScratchpad(
                target_seq, target_crc, action.value - 1, param
            )

        except GLib.Error as e:
            ret = ReturnCode.error_from_dbus_exception(str(e))
            logging.warning("Cannot set target scratchpad: %s (can be normal if same value as already set)", ret.name)

        return ret


class SinkManager:
    "Helper class to manage the Sink list"

    def __init__(
        self, bus, on_new_sink_cb, on_sink_removal_cb, on_stack_started, on_stack_stopped
    ):

        self.sinks = {}
        # List used to quickly retrieved sink well known name
        self.sender_to_name = {}
        self.bus = bus

        self.add_cb = None
        self.rm_cb = None
        self.stack_started_cb = on_stack_started
        self.stack_stopped_cb = on_stack_stopped

        bus_monitor = self.bus.get("org.freedesktop.DBus")

        # Find sinks already on bus
        for name in bus_monitor.ListNames():
            if name.startswith(DBUS_SINK_PREFIX):
                short_name = name[len(DBUS_SINK_PREFIX) :]
                self._add_sink(short_name, bus_monitor.GetNameOwner(name))

        # Monitor the bus for connections
        self.bus.subscribe(
            sender="org.freedesktop.DBus",
            signal="NameOwnerChanged",
            signal_fired=self._on_name_owner_changed,
        )

        # Set them at the end to be sure Sink Manager is ready when cb are fired
        self.add_cb = on_new_sink_cb
        self.rm_cb = on_sink_removal_cb

    def _add_sink(self, short_name, unique_name):
        if short_name in self.sinks:
            logging.warning("Sink already in list sink name=%s", short_name)
            return

        # Open proxy for this sink
        proxy = self.bus.get(
            DBUS_SINK_PREFIX + short_name,  # Bus name
            "/com/wirepas/sink",  # Object path
        )

        sink = Sink(
            bus=self.bus,
            proxy=proxy,
            sink_id=short_name,
            unique_name=unique_name,
            on_stack_started=self.stack_started_cb,
            on_stack_stopped=self.stack_stopped_cb,
        )

        sink.register_for_stack_started()
        sink.register_for_stack_stopped()

        self.sinks[short_name] = sink

        self.sender_to_name[unique_name] = short_name

        if self.add_cb is not None:
            self.add_cb(short_name)

        logging.info("New sink added with name %s", short_name)

    def _remove_sink(self, short_name):
        try:
            sink = self.sinks.pop(short_name)
            sink.unregister_from_stack_started()
            sink.unregister_from_stack_stopped()

            # Remove Sink to association list
            for k, v in self.sender_to_name.items():
                if v == short_name:
                    self.sender_to_name.pop(k)
                    logging.warning("Association removed from %s => %s", k, v)
                    break

            # call client cb
            if self.rm_cb is not None:
                self.rm_cb(short_name)
        except KeyError:
            logging.error("Cannot remove %s from sink list", short_name)

        logging.info("Sink removed with name %s", short_name)

    def _on_name_owner_changed(self, sender, object, iface, signal, params):
        # pylint: disable=unused-argument
        # pylint: disable=redefined-builtin
        well_known_name = params[0]
        if well_known_name.startswith(DBUS_SINK_PREFIX):
            short_name = well_known_name[len(DBUS_SINK_PREFIX) :]
            # Owner change on a sink, check if it is removal or addition
            old_owner = params[1]
            new_owner = params[2]
            if old_owner == "":
                # New sink connection
                self._add_sink(short_name, new_owner)
            elif new_owner == "":
                # Removal
                self._remove_sink(short_name)
            else:
                logging.critical(
                    "Not addition nor removal ??? %s: %s => %s",
                    well_known_name,
                    old_owner,
                    new_owner,
                )

    def get_sinks(self):
        # Return a list that is a copy to avoid modification
        # of list while iterating on it (if new sink is connected)
        return list(self.sinks.values())

    def get_sink_name(self, bus_name):
        try:
            return self.sender_to_name[bus_name]
        except KeyError:
            logging.error("Unknown sink %s from sink list", bus_name)
            return None

    def get_sink(self, short_name):
        try:
            return self.sinks[short_name]
        except KeyError:
            logging.error("Unknown sink %s from sink list", short_name)
            return None
