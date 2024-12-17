import logging
import os

from pythonjsonlogger import jsonlogger

import settings

LOGGING_MESSAGE_FORMAT = "%(asctime)s %(name)-12s %(levelname)s %(message)s"

def _get_file_logger() -> logging.FileHandler:
    os.makedirs(os.path.dirname(settings.LOG_FILE_PATH), exist_ok=True)
    file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
    file_handler.setLevel(logging.DEBUG)
    return file_handler


def _get_console_logger() -> logging.StreamHandler:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    return console_handler


def _apply_default_formatter(handler: logging.Handler):
    formatter = jsonlogger.JsonFormatter(LOGGING_MESSAGE_FORMAT)
    handler.setFormatter(formatter)

class APILogger:
    def __init__(self, _logger=None):
        self.logger: logging.Logger = _logger

    @classmethod
    def start_logger(cls):
        name = settings.APPLICATION_NAME
        file_handler = _get_file_logger()
        console_handler = _get_console_logger()
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.DEBUG)

        _logger.addHandler(console_handler)
        _logger.addHandler(file_handler)
        _apply_default_formatter(file_handler)
        _apply_default_formatter(console_handler)
        return cls(_logger=_logger)

    def get(self):
        return self.logger

# Singleton logger, used across the application
api_logger: APILogger = APILogger.start_logger()

