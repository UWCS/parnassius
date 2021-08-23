import asyncio
import logging
import sys
from functools import wraps
from inspect import getfile, getsourcelines, signature
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import confuse

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


def get_representation(arg):
    if type(arg).__repr__ is not object.__repr__:
        return repr(arg)
    elif type(arg).__str__ is not object.__str__:
        return str(arg)
    else:
        return repr(arg)


def log_func(logger: logging.Logger):
    def decorator(func):
        def log_call(f, *args, **kwargs):
            args_repr = [get_representation(a) for a in args]
            kwargs_repr = [f"{k}={get_representation(v)}" for k, v in kwargs.items()]
            function_signature = f"{f.__name__}{signature(f)}"
            arguments = ", ".join(args_repr + kwargs_repr)
            logger.debug(f"Calling {function_signature}")
            logger.debug(
                f"{f.__name__} is defined in {getfile(f)} on line {getsourcelines(f)[-1]}"
            )
            logger.debug(f"Arguments: {arguments}")

        def log_result(f, r):
            logger.debug(f"{f.__name__} returned {get_representation(r)}")

        @wraps(func)
        def wrapper(*args, **kwargs):
            log_call(func, *args, **kwargs)
            result = func(*args, **kwargs)
            log_result(func, result)
            return result

        @wraps(func)
        async def coro_wrapper(*args, **kwargs):
            log_call(func, *args, **kwargs)
            result = await func(*args, **kwargs)
            log_result(func, result)
            return result

        if asyncio.iscoroutinefunction(func):
            return coro_wrapper
        else:
            return wrapper

    return decorator
