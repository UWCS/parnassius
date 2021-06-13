import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from config import CONFIG

__all__ = ["setup_logging"]


def setup_logging():
    _handler = TimedRotatingFileHandler(
        Path(
            CONFIG["logging"]["location"].get(str),
            CONFIG["logging"]["filename"].get(str),
        ),
        when="midnight",
        interval=1,
    )
    _handler.suffix = CONFIG["logging"]["suffix"].get(str)
    _formatter = logging.Formatter(
        fmt="{asctime}:{name}:{levelname}:{message}",
        style="{",
    )
    _handler.setFormatter(_formatter)
    ROOT_LOGGER = logging.getLogger()
    ROOT_LOGGER.addHandler(_handler)
    _level = CONFIG["logging"]["level"].as_choice(
        {
            "NOTSET": logging.NOTSET,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "WARN": logging.WARN,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "FATAL": logging.FATAL,
        }
    )
    ROOT_LOGGER.setLevel(_level)
