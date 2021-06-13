import logging
import subprocess

from discord.ext.commands import Bot, Cog, Context, command

from utils.logging import log_func

__all__ = ["Misc"]

logger = logging.getLogger("parnassius.cogs.commands.misc")
log = log_func(logger)


class Misc(Cog):
    @log
    def __init__(self, bot: Bot):
        self.bot = bot
        self.version = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True
        ).stdout.decode()

    @command()
    @log
    async def ping(self, ctx: Context):
        """Pong!"""
        await ctx.send(":ping_pong:")

    @command()
    @log
    async def version(self, ctx: Context):
        """Print the hash of the most recent commit."""
        await ctx.send(self.version)


@log
def setup(bot: Bot):
    bot.add_cog(Misc(bot))
