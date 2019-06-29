# https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# https://www.toptal.com/python/in-depth-python-logging
import logging
import sys
from logging.handlers import RotatingFileHandler

LOG_FORMATTER = logging.Formatter("%(asctime)s[%(name)s][%(levelname)s]: %(message)s", datefmt='%Y-%m-%dT%H:%M:%S%z')


def get_console_handler(log_level):

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(LOG_FORMATTER)
    console_handler.setLevel(log_level)
    return console_handler


def get_file_handler(log_file, log_level):

    # https://docs.python.org/3/library/logging.handlers.html
    # Set write mode to append https://docs.python.org/3/library/functions.html#filemodes
    file_handler = RotatingFileHandler(log_file, mode='a', maxBytes=1000000, backupCount=10)
    file_handler.setFormatter(LOG_FORMATTER)
    file_handler.setLevel(log_level)
    return file_handler


def get_logger_with_name(log_name, log_level_console="INFO", log_filename="", log_level_file="INFO"):

    logger = logging.getLogger(log_name)
    # With this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    # Set the root logger to the lowest level so its handlers set logging limits instead
    logger.setLevel(logging.DEBUG)

    # If the logger was initialized earlier, an old handler might be hanging around. Remove it.
    for handler in logger.handlers:
        logger.removeHandler(handler)

    logger.addHandler(get_console_handler(log_level_console))

    # Only add a Handler for file logging if the file path passed in is not empty
    if not log_filename == "":
        logger.debug("Adding handler for log file %s with log level %s", log_filename, log_level_file)
        logger.addHandler(get_file_handler(log_filename, log_level_file))

    return logger
