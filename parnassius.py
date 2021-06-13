#!/usr/bin/env python3
import logging

from discord.ext.commands import Bot

from config import CONFIG
from utils.logging import setup_logging

EXTENSIONS = ["cogs.commands.misc"]

bot = Bot(CONFIG["discord"]["prefix"].get(str))


@bot.event
async def on_ready():
    logger = logging.getLogger("parnassius")
    logger.info(f"Logged in as {bot.user}")
    logger.info(f"Connected to {len(bot.guilds)} guilds")


def main():
    setup_logging()
    logger = logging.getLogger("parnassius")
    logger.info("Parnissius is starting")
    for extension in EXTENSIONS:
        try:
            logger.info(f"Loading extension {extension}")
            bot.load_extension(extension)
        except Exception as e:
            logger.exception(e)
            raise e

    logger.info("Connecting to Discord")
    bot.run(CONFIG["discord"]["token"].get(str))


if __name__ == "__main__":
    main()
