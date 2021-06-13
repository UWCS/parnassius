#!/usr/bin/env python3
import logging

from discord.ext.commands import Bot

from config import CONFIG
from utils.logging import setup_logging

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
ROOT_LOGGER.setLevel(logging.INFO)


bot = Bot(CONFIG["discord"]["prefix"].get(str))


@bot.event
async def on_ready():
    logger = logging.getLogger("parnassius")
    logger.info(f"Logged in as {bot.user}")
    logger.info(f"Connected to {len(bot.guilds)} guilds")


def main():
    setup_logging()
    logger = logging.getLogger("parnassius")
    logger.debug(f"{main.__name__} start")
    logger.info("Parnissius is starting")
    for extension in EXTENSIONS:
        try:
            logger.info(f"Loading extension {extension}")
            bot.load_extension(extension)
        except Exception as e:
            logger.exception(e)

    logger.info("Connecting to Discord")
    bot.run(CONFIG["discord"]["token"].get(str))
    logger.debug(f"{main.__name__} end")


if __name__ == "__main__":
    main()
