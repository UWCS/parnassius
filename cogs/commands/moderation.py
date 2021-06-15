import logging
from datetime import datetime
from functools import cached_property
from typing import Optional, Union

import humanize
from discord import Guild, HTTPException, Member, Role
from discord.ext.commands import Bot, Cog, Context, Greedy, command, group
from discord.utils import get
from sqlalchemy.exc import NoResultFound

from cogs.database import Database
from config import CONFIG
from models import (
    ActionType,
    ModerationAction,
    ModerationLinkedAction,
    ModerationTemporaryAction,
    User,
)
from utils.DateTimeConverter import DateTimeConverter
from utils.Greedy1 import Greedy1Command, Greedy1Group
from utils.logging import log_func
from utils.utils import format_list_of_members

__all__ = ["Moderation"]


logger = logging.getLogger("parnassius.cogs.commands.moderation")
log = log_func(logger)


class Moderation(Cog):
    @log
    def __init__(self, bot: Bot):
        self.bot = bot

    @cached_property
    def guild(self) -> Guild:
        return get(self.bot.guilds, id=CONFIG["guild"]["id"].get(int))

    @cached_property
    def muted_role(self) -> Role:
        return get(self.guild.roles, id=CONFIG["guild"]["roles"]["muted"].get(int))

    @log
    async def add_moderation_history_item(
        self,
        user: Union[User, Member],
        action_type: ActionType,
        reason: Optional[str],
        moderator: Union[User, Member],
        until: Optional[datetime] = None,
        linked_action_id: Optional[int] = None,
    ):
        db = await Database.get(self.bot)
        user_id = db.get_user(user).scalars().one().id
        moderator_id = db.get_user(moderator).scalars().one().id
        with db.session() as session:
            action = ModerationAction(
                user_id=user_id,
                action=action_type,
                reason=reason,
                moderator_id=moderator_id,
            )
            session.add(action)
            # Flush here to generate primary key
            session.flush()
            if until is not None:
                temp_action = ModerationTemporaryAction(
                    id=action.id,
                    until=until,
                )
                session.add(temp_action)
            if linked_action_id is not None:
                linked_action = ModerationLinkedAction(
                    id=action.id,
                    linked_action=linked_action_id,
                )
                session.add(linked_action)
            session.commit()

    @log
    async def partition_members(self, members, action):
        async def predicate(member):
            try:
                await action(member)
                return True
            except (HTTPException, NoResultFound) as e:
                logger.exception(e)
                return False

        results = [await predicate(member) for member in members]
        failed = [m for m, r in zip(members, results) if not r]
        muted = [m for m, r in zip(members, results) if r]
        return failed, muted

    @log
    async def create_message_parts(self, action_type, failed, muted, reason, until):
        message_parts = []
        if len(muted) > 0:
            mentions = format_list_of_members(muted)
            with_reason = (
                "with no reason given"
                if reason is None
                else f"with the reason \n> {reason}"
            )
            were = "was" if len(muted) == 1 else "were"
            until_datetime = (
                ""
                if until is None
                else f" until {humanize.naturaltime(until)} (a duration of {humanize.precisedelta(until - datetime.now())})"
            )

            message_parts.append(
                f"{action_type.emoji} **{action_type.past_tense.upper()}** {action_type.emoji}\n"
                f"{mentions} {were} {action_type.past_tense}{until_datetime} {with_reason}"
            )
        if len(failed) > 0:
            mentions = format_list_of_members(failed)
            message_parts.append(f"Failed to mute {mentions}")

        return message_parts

    @log
    async def moderation_command(
        self, ctx, members, reason, action, action_type, moderator, until=None
    ):
        logger.info(f"{moderator} used {action_type} with reason {reason}")
        failed, muted = await self.partition_members(members, action)
        message_parts = await self.create_message_parts(
            action_type, failed, muted, reason, until
        )
        await ctx.send("\n".join(message_parts))

    @command(cls=Greedy1Command)
    @log
    async def tempmute(
        self,
        ctx: Context,
        members: Greedy[Member],
        until: DateTimeConverter,
        *,
        reason: Optional[str],
    ):
        moderator = ctx.author
        action_type = ActionType.TEMPMUTE

        async def action(member):
            await member.add_roles(self.muted_role, reason=reason)
            await self.add_moderation_history_item(
                member, action_type, reason, moderator, until=until
            )
            logger.info(f"Applied {action_type} to {member}")

        await self.moderation_command(
            ctx, members, reason, action, action_type, moderator, until
        )

    @command(cls=Greedy1Command)
    @log
    async def mute(
        self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]
    ):
        moderator = ctx.author
        action_type = ActionType.MUTE

        async def action(member):
            await member.add_roles(self.muted_role, reason=reason)
            await self.add_moderation_history_item(
                member, action_type, reason, moderator
            )
            logger.info(f"Applied {action_type} to {member}")

        await self.moderation_command(
            ctx, members, reason, action, action_type, moderator
        )

    @command(cls=Greedy1Command)
    @log
    async def unmute(
        self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]
    ):
        moderator = ctx.author
        action_type = ActionType.UNMUTE

        async def action(member):
            await member.remove_roles(self.muted_role, reason=reason)
            await self.add_moderation_history_item(
                member, action_type, reason, moderator
            )
            logger.info(f"Applied {action_type} to {member}")

        await self.moderation_command(
            ctx, members, reason, action, action_type, moderator
        )

    @group(cls=Greedy1Group)
    @log
    async def warn(self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]):
        moderator = ctx.author
        action_type = ActionType.WARN

        async def action(member):
            channel = member.dm_channel or await member.create_dm()
            with_reason = (
                "with no reason given."
                if reason is None
                else f"with the following reason: \n> {reason}"
            )
            warning = (
                f"{action_type.emoji} **WARNING** {action_type.emoji}\n"
                f"You have been warned in UWCS {with_reason}"
            )
            await channel.send(warning)
            await self.add_moderation_history_item(member, action_type, reason, moderator)
            logger.info(f"Warned {member}")

        await self.moderation_command(ctx, members, reason, action, action_type, moderator)


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
