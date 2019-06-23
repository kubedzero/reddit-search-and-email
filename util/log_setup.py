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
def get_logger_with_name(log_name, log_file, log_level_file, log_level_console):
    logger = logging.getLogger(log_name)
    logger.addHandler(get_console_handler(log_level_console))
    logger.addHandler(get_file_handler(log_file, log_level_file))
    # with this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    # set the root logger to the lowest level so its handlers set logging limits instead
    logger.setLevel(logging.DEBUG)
    return logger