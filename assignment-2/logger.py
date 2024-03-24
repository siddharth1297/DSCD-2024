"""
Logger
https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings
"""

import logging as __logging
import os as __os

LOGS_LOGGER = None
METADATA_LOGGER = None
DUMP_LOGGER = None

# pylint: disable=line-too-long
__FORMATTER = __logging.Formatter(
    "%(asctime)s.%(msecs)03d %(levelname)s [%(filename)s:%(funcName)s:%(lineno)d] [%(node)s] -- %(message)s",
    "%H:%M:%S",
)


def __create_logs_dir(logs_dir: str):
    """Creates the logging directory structure"""
    try:
        __os.makedirs(logs_dir)
    except OSError:
        pass
    try:
        __os.remove(logs_dir + "dump.txt")
    except OSError:
        pass
    """
    try:
        __os.remove(logs_dir + "metadata.txt")
    except OSError:
        pass
    try:
        __os.remove(logs_dir + "logs.txt")
    except OSError:
        pass
    """


def __setup_logger(name, log_file, prefix, level):
    """To setup as many loggers as you want"""

    handler = __logging.FileHandler(log_file)
    handler.setFormatter(__FORMATTER)

    logger = __logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    logger = __logging.LoggerAdapter(logger, extra={"node": prefix})
    return logger


def set_logger(logs_dir: str, prefix: str, level):
    """Sets logger"""
    __create_logs_dir(logs_dir)
    # pylint: disable=global-statement
    global LOGS_LOGGER, METADATA_LOGGER, DUMP_LOGGER
    #LOGS_LOGGER = __setup_logger("logs", logs_dir + "logs.txt", prefix, level)
    #METADATA_LOGGER = __setup_logger(
    #    "metadata", logs_dir + "metadata.txt", prefix, level
    #)
    DUMP_LOGGER = __setup_logger("dump", logs_dir + "dump.txt", prefix, level)


def create_manual_logger(file_name: str, rejoin: bool) -> None:
    """
    Create fd loggers
    """
    if not rejoin:
        try:
            __os.remove(file_name)
        except OSError:
            pass

    mode = "r+" if __os.path.isfile(file_name) else "w+"
    fd = open(file_name, mode, encoding= 'UTF-8')
    return fd