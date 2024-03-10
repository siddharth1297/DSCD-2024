"""
Logger
https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings
"""

import logging
import os

LOGS_LOGGER = None
METADATA_LOGGER = None
DUMP_LOGGER = None

FORMATTER = logging.Formatter(
    "%(asctime)s-%(levelname)s-[%(pathname)s:%(funcName)s:%(lineno)d] -- %(message)s"
)


def create_logs_dir(logs_dir: str):
    """Creates the logging directory structure"""
    try:
        os.makedirs(logs_dir)
    except OSError:
        pass
    try:
        os.remove(logs_dir + "logs.txt")
    except OSError:
        pass
    try:
        os.remove(logs_dir + "metadata.txt")
    except OSError:
        pass
    try:
        os.remove(logs_dir + "dump.txt")
    except OSError:
        pass


def setup_logger(name, log_file, level):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)
    handler.setFormatter(FORMATTER)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def set_logger(logs_dir: str, level):
    """Sets logger"""
    create_logs_dir(logs_dir)
    # pylint: disable=W0603
    global LOGS_LOGGER, METADATA_LOGGER, DUMP_LOGGER
    LOGS_LOGGER = setup_logger("logs", logs_dir + "logs.txt", level)
    METADATA_LOGGER = setup_logger("metadata", logs_dir + "metadata.txt", level)
    DUMP_LOGGER = setup_logger("dump", logs_dir + "dump.txt", level)
