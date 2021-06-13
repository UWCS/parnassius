import logging
import subprocess

from discord.ext.commands import Bot, Cog, Context, command

logger = logging.getLogger("parnassius.cogs.commands.misc")


class Misc(Cog):
    def __init__(self, bot: Bot):
        logger.debug(f"{type(self).__name__} __init__ start")
        self.bot = bot
        self.version = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True
        ).stdout.decode()
        logger.debug(f"{type(self).__name__} __init__ end")

    @command()
    async def ping(self, ctx: Context):
        """Pong!"""
        logger.debug(f"{self.ping.callback.__name__} start")
        await ctx.send(":ping_pong:")
        logger.debug(f"{self.ping.callback.__name__} end")

    @command()
    async def version(self, ctx: Context):
        """Print the hash of the most recent commit."""
        logger.debug(f"{self.ping.callback.__name__} start")
        await ctx.send(self.version)
        logger.debug(f"{self.ping.callback.__name__} end")


def setup(bot: Bot):
    bot.add_cog(Misc(bot))
