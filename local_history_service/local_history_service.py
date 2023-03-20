# Copyright 2023 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.

import os
import sys
from datetime import datetime, timedelta
import argparse
import logging
import base64

from wirepas_gateway.dbus.dbus_client import BusClient
from wirepas_gateway import __pkg_name__


class LocalHistoryService(BusClient):
    def __init__(self, historical_days=5, file_path="", file_prefix="lhs", endpoints=None) -> None:

        super(LocalHistoryService, self).__init__(
            ignored_ep_filter=None
        )

        self.historical_days = historical_days
        self.file_path = file_path
        self.file_prefix = file_prefix
        self.endpoints = endpoints

        logging.info("Local history service started for %d days for EPs: %s", historical_days, endpoints)

    def on_data_received(
        self,
        sink_id,
        timestamp,
        src,
        dst,
        src_ep,
        dst_ep,
        travel_time,
        qos,
        hop_count,
        data,
    ):
        if dst_ep not in self.endpoints:
            logging.debug("Filtered EPs")
            return

        # Get current time
        now = datetime.now()

        # Compute the file name
        file_suffix = now.strftime("_%d_%m_%Y")
        target_file = os.path.join(self.file_path, self.file_prefix + file_suffix)

        logging.info("Packet received to be written to %s", target_file)

        # Check if we have created the file
        file_created = not os.path.exists(target_file)

        with open(target_file, 'a') as cur_file:
            cur_file.write("%d;%x;%d;%d;%s\n" % (
                now.timestamp(),
                src,
                src_ep,
                dst_ep,
                base64.b64encode(data))
            )

        if file_created:
            # File was created, check if we have to remove an older one
            logging.info("Check if a file must be deleted")
            file_suffix_to_remove = (now - timedelta(days=(self.historical_days + 1))).strftime("_%d_%m_%Y")
            file_to_remove = os.path.join(self.file_path, self.file_prefix + file_suffix_to_remove)

            try:
                logging.debug("Trying to remove file %s", file_to_remove)
                os.remove(file_to_remove)
            except OSError:
                logging.debug("No file to remove")


def str2none(value):
    """ Ensures string to bool conversion """
    if value == "":
        return None
    return value


def parse_setting_list(list_setting):
    """ This function parse ep list specified from setting file or cmd line

    Input list has following format [1, 5, 10-15] as a string or list of string
    and is expended as a single list [1, 5, 10, 11, 12, 13, 14, 15]

    Args:
        list_setting(str or list): the list from setting file or cmd line.

    Returns: A single list of ep
    """
    if isinstance(list_setting, str):
        # List is a string from cmd line
        list_setting = list_setting.replace("[", "")
        list_setting = list_setting.replace("]", "")
        list_setting = list_setting.split(",")

    single_list = []
    for ep in list_setting:
        # Check if ep is directly an int
        if isinstance(ep, int):
            if ep < 0 or ep > 255:
                raise SyntaxError("EP out of bound")
            single_list.append(ep)
            continue

        # Check if ep is a single ep as string
        try:
            ep = int(ep)
            if ep < 0 or ep > 255:
                raise SyntaxError("EP out of bound")
            single_list.append(ep)
            continue
        except ValueError:
            # Probably a range
            pass

        # Check if ep is a range
        try:
            ep = ep.replace("'", "")
            lower, upper = ep.split("-")
            lower = int(lower)
            upper = int(upper)
            if lower > upper or lower < 0 or upper > 255:
                raise SyntaxError("Wrong EP range value")

            single_list += list(range(lower, upper + 1))
        except (AttributeError, ValueError):
            raise SyntaxError("Wrong EP range format")

    if len(single_list) == 0:
        single_list = None

    return single_list


if __name__ == "__main__":
    debug_level = os.environ.get("WM_DEBUG_LEVEL", "info")
    # Convert it in upper for logging config
    debug_level = "{0}".format(debug_level.upper())

    # enable its logger
    logging.basicConfig(
        format=f'%(asctime)s | [%(levelname)s] {__pkg_name__}@%(filename)s:%(lineno)d:%(message)s',
        level=debug_level,
        stream=sys.stdout
    )

    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')

    parser.add_argument(
        "--historical_days",
        default=os.environ.get("WM_LHS_NUM_DAYS", 5),
        action="store",
        type=int,
        help="Number of historical days to store (1 file per day)",
    )

    parser.add_argument(
        "--historical_file_path",
        default=os.environ.get("WM_LHS_PATH", ""),
        action="store",
        type=str,
        help="Path to store files",
    )

    parser.add_argument(
        "--endpoints_to_save",
        type=str2none,
        default=os.environ.get("WM_LHS_ENDPOINTS", None),
        help=("Destination endpoints list to keep in history (all if not set)"),
    )

    args = parser.parse_args()

    LocalHistoryService(args.historical_days, args.historical_file_path, endpoints=parse_setting_list(args.endpoints_to_save)).run()
