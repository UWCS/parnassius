import logging
import sys
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import confuse
from AtLog.atlog import get_representation, log_func

from config import CONFIG

__all__ = ["setup_logging", "get_representation", "log_func"]


def setup_logging():
    logging_path = Path(
        CONFIG["logging"]["location"].get(confuse.Path(in_source_dir=True)),
        CONFIG["logging"]["filename"].get(str),
    )
    # Create the directory if it does not already exist
    logging_path.parent.mkdir(mode=775, parents=True, exist_ok=True)
    formatter = logging.Formatter(
        fmt="{asctime}:{name}:{levelname}:{message}",
        style="{",
    )
    filter_ = logging.Filter("parnassius")

    file_handler = TimedRotatingFileHandler(
        logging_path,
        when="midnight",
        interval=1,
    )
    file_handler.suffix = CONFIG["logging"]["suffix"].get(str)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(filter_)

    stdout_handler = StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(filter_)

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stdout_handler)

    level = CONFIG["logging"]["level"].as_choice(
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
    root_logger.setLevel(level)
