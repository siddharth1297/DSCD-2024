"""
Logger
https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings
"""

import logging as __logging
import os as __os

LOGS_LOGGER = None
METADATA_LOGGER = None
DUMP_LOGGER = None

__FORMATTER = __logging.Formatter(
    "%(asctime)s-%(levelname)s-[%(pathname)s:%(funcName)s:%(lineno)d] -- %(message)s"
)


def __create_logs_dir(logs_dir: str):
    """Creates the logging directory structure"""
    try:
        __os.makedirs(logs_dir)
    except OSError:
        pass
    try:
        __os.remove(logs_dir + "logs.txt")
    except OSError:
        pass
    try:
        __os.remove(logs_dir + "metadata.txt")
    except OSError:
        pass
    try:
        __os.remove(logs_dir + "dump.txt")
    except OSError:
        pass


def __setup_logger(name, log_file, level):
    """To setup as many loggers as you want"""

    handler = __logging.FileHandler(log_file)
    handler.setFormatter(__FORMATTER)

    logger = __logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def set_logger(logs_dir: str, level):
    """Sets logger"""
    __create_logs_dir(logs_dir)
    # pylint: disable=global-statement
    global LOGS_LOGGER, METADATA_LOGGER, DUMP_LOGGER
    LOGS_LOGGER = __setup_logger("logs", logs_dir + "logs.txt", level)
    METADATA_LOGGER = __setup_logger("metadata", logs_dir + "metadata.txt", level)
    DUMP_LOGGER = __setup_logger("dump", logs_dir + "dump.txt", level)
