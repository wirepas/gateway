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


def setup_log(
    module,
    level="debug",
    log_format="%(asctime)s | [%(levelname)s] %(name)s@%(filename)s:%(lineno)d:%(message)s",
):
    """
    Prepares logging.

    Setups Python's logging and by default send up to LEVEL
    logs to stdout.

    Args:
        level - logging level to enable.
    """

    logger = logging.getLogger(module)
    level = "{0}".format(level.upper())

    try:
        logger.setLevel(eval("logging.{0}".format(level)))
    except:
        logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(log_format)

    # configures stdout
    h = logging.StreamHandler(stream=sys.stdout)
    h.setFormatter(formatter)

    logger.addHandler(h)

    return logger
