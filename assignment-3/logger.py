"""
Logger
"""
import logging as __logging
import os as __os

DUMP_LOGGER = None

# pylint: disable=line-too-long
__FORMATTER = __logging.Formatter(
    "%(asctime)s.%(msecs)03d %(levelname)s [%(filename)s:%(funcName)s:%(lineno)d] [%(node)s] -- %(message)s",
    "%H:%M:%S",
)


def __create_logs_dir(logs_dir: str, log_file_name: str):
    """Creates the logging directory structure"""
    try:
        __os.makedirs(logs_dir)
    except OSError:
        pass
    try:
        __os.remove(logs_dir + log_file_name)
    except OSError:
        pass


def __setup_logger(name, log_file, prefix, level):
    """To setup as many loggers as you want"""

    handler = __logging.FileHandler(log_file)
    handler.setFormatter(__FORMATTER)

    logger = __logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    logger = __logging.LoggerAdapter(logger, extra={"node": prefix})

    return logger


def set_logger(logs_dir: str, log_file_name: str, prefix: str, level):
    """Sets logger"""
    __create_logs_dir(logs_dir, log_file_name)
    # pylint: disable=global-statement
    global DUMP_LOGGER
    DUMP_LOGGER = __setup_logger("dump", logs_dir + log_file_name, prefix, level)
