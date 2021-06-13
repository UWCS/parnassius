import logging

from discord.ext.commands import Bot, Cog, Context, command

logger = logging.getLogger("parnassius.cogs.commands.misc")


class Misc(Cog):
    def __init__(self, bot: Bot):
        logger.debug(f"{type(self).__name__} __init__ start")
        self.bot = bot
        logger.debug(f"{type(self).__name__} __init__ end")

    @command()
    async def ping(self, ctx: Context):
        """Pong!"""
        logger.debug(f"{self.ping.callback.__name__} start")
        await ctx.send(":ping_pong:")
        logger.debug(f"{self.ping.callback.__name__} end")


def setup(bot: Bot):
    bot.add_cog(Misc(bot))
