from __future__ import annotations

import logging
import unicodedata
from typing import List, Optional

from discord import Message
from discord.ext.commands import Bot, Cog
from sqlalchemy import func
from sqlalchemy.future import select

from cogs.commands.moderation import Moderation
from cogs.database import Database
from cogs.logging import Logging
from config import CONFIG
from models import ActionType, ModerationAction, ModerationLinkedAction, User
from utils.logging import log_func

__all__ = ["Automod"]


logger = logging.getLogger("parnassius.cogs.automod")
log = log_func(logger)


class Automod(Cog):
    @log
    def __init__(self, bot: Bot):
        self.bot = bot
        self._engine = None

    @property
    @log
    def forbidden_words(self) -> List[str]:
        return CONFIG["forbidden_words"].as_str_seq()

    @log
    def matches(self, content) -> Optional[str]:
        content = content.casefold()
        content = unicodedata.normalize("NFKD", content)
        content = "".join(c for c in content if not unicodedata.combining(c))
        return next((w for w in self.forbidden_words if w in content), None)

    @Cog.listener()
    @log
    async def on_message(self, message: Message):
        if message.author.bot or (word := self.matches(message.content)) is None:
            return

        await message.delete()
        moderation = await Moderation.get(self.bot)
        logging_cog = await Logging.get(self.bot)
        channel = self.bot.get_channel(logging_cog.channels["moderation"].get(int))
        moderator = self.bot.user
        reason = f"Automod: {message.content}"

        db = await Database.get(self.bot)
        with db.session() as session:
            user_id = db.get_or_create_user(message.author).id
            query = (
                select(ModerationLinkedAction.linked_id)
                .join(ModerationLinkedAction.moderation_action)
                .where(
                    ModerationAction.user_id == user_id,
                    ModerationAction.action == ActionType.REMOVE_AUTOWARN,
                )
            )
            removed = session.execute(query).scalars().all()
            logger.debug(removed)
            query = (
                select(func.count(ModerationAction.id))
                .join(ModerationAction.user)
                .where(
                    User.id == user_id,
                    ModerationAction.action.in_(
                        [ActionType.AUTOWARN, ActionType.AUTOMUTE]
                    ),
                    ModerationAction.id.notin_(removed),
                )
            )
            number_warnings = session.execute(query).scalars().one()
            logger.debug(number_warnings)

        if number_warnings < 2:
            action_type = ActionType.AUTOWARN

            async def action(member):
                dms = member.dm_channel or await member.create_dm()
                warning = (
                    f"{action_type.emoji} **AUTOMATIC WARNING** {action_type.emoji}\n"
                    f"You have been automatically warned in UWCS for saying {word}."
                )
                await dms.send(warning)
                await moderation.add_moderation_history_item(
                    member, action_type, reason, moderator
                )
                logging.info(f"{action_type.past_tense.capitalize()} {member}")

        elif number_warnings < 4:
            action_type = ActionType.AUTOMUTE

            async def action(member):
                await member.add_roles(moderation.muted_role, reason=reason)
                dms = member.dm_channel or await member.create_dm()
                warning = (
                    f"{action_type.emoji} **AUTOMATIC MUTE** {action_type.emoji}\n"
                    f"You have been automatically muted in UWCS for saying {word}."
                )
                await dms.send(warning)
                await moderation.add_moderation_history_item(
                    member, action_type, reason, moderator
                )
                logging.info(f"{action_type.past_tense.capitalize()} {member}")

        else:
            action_type = ActionType.BAN

            async def action(member):
                dms = member.dm_channel or await member.create_dm()
                warning = (
                    f"{action_type.emoji} **AUTOMATIC BAN** {action_type.emoji}\n"
                    f"You have been muted three times; prepare for destruction."
                )
                await dms.send(warning)
                await member.ban(reason=reason)
                await moderation.add_moderation_history_item(
                    member, action_type, reason, moderator
                )
                logging.info(f"{action_type.past_tense.capitalize()} {member}")

        await moderation.moderation_command(
            channel, [message.author], reason, action, action_type, moderator
        )


def setup(bot):
    bot.add_cog(Automod(bot))
