import logging
from typing import Optional, Union

from discord import HTTPException, Message, TextChannel
from discord.ext.commands import Bot, Cog, Context, command

__all__ = ["Channel"]

from config import CONFIG
from utils.logging import log_func
from utils.NaturalConverter import NaturalConverter

logger = logging.getLogger("parnassius.cogs.commands.channel")
log = log_func(logger)


class Channel(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.lockdown_extra_roles = CONFIG["guild"]["roles"][
            "lockdown_extra_roles"
        ].get(list)

    @command()
    @log
    async def purge(
        self,
        ctx: Context,
        message: Union[NaturalConverter, Message],
        channel: Optional[TextChannel],
    ):
        """Purge the last N messages in a given channel, or alternatively every message since one provided."""
        if isinstance(message, int):
            # Purge the last N messages
            if channel is None:
                channel = ctx.channel
            same_channel = ctx.channel == channel
            # Add 1 to account for the command that triggered the purge
            offset = 1 if same_channel else 0
            try:
                deleted = await channel.purge(
                    check=lambda _: True, limit=message + offset, bulk=True
                )
                logger.info(
                    f"{ctx.author} purged the most recent {len(deleted)} message{'s' if len(deleted) != 1 else ''} from {channel}"
                )
            except HTTPException as e:
                logger.info(
                    f"{ctx.author} failed to purge the most recent {message} message{'s' if message != 1 else ''} from {channel}"
                )
                logger.exception(e)
        elif isinstance(message, Message):
            # Purge everything since this message
            try:
                deleted = await message.channel.purge(after=message.created_at)
                # Since after does not include the message itself, we must add it manually
                await message.delete()
                deleted.append(message)
                logger.info(
                    f"{ctx.author} purged the most recent "
                    f"{len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                    f"from {channel} "
                    f"(since {message.jump_url}, created at {message.created_at})"
                )
            except HTTPException as e:
                logger.info(
                    f"{ctx.author} failed to purge messages since {message.jump_url} from {channel}"
                )
                logger.exception(e)


def setup(bot: Bot):
    bot.add_cog(Channel(bot))
