# from __future__ import annotations

import logging
from datetime import datetime
from functools import cached_property
from typing import Optional, Union

import humanize
from discord import Guild, HTTPException, Member, Role, User as DiscordUser
from discord.ext.commands import Bot, Cog, Context, Greedy, command, group
from discord.utils import get
from sqlalchemy.exc import NoResultFound
from sqlalchemy.future import select

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

    @classmethod
    @log
    async def get(cls, bot: Bot) -> "Moderation":
        await bot.wait_until_ready()
        return bot.get_cog(cls.__name__)

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
        user_id = db.get_or_create_user(user).id
        moderator_id = db.get_or_create_user(moderator).id
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
                    linked_id=linked_action_id,
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
            # noinspection PyTypeChecker
            # In this scenario, `until` is a `datetime` and not a `DateTimeConverter`.
            await self.add_moderation_history_item(
                member, action_type, reason, moderator, until=until
            )
            logging.info(f"{action_type.past_tense.capitalize()} {member}")

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
            logging.info(f"{action_type.past_tense.capitalize()} {member}")

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
            logging.info(f"{action_type.past_tense.capitalize()} {member}")

        await self.moderation_command(
            ctx, members, reason, action, action_type, moderator
        )

    @group(cls=Greedy1Group, invoke_without_command=True)
    @log
    async def warn(
        self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]
    ):
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
            await self.add_moderation_history_item(
                member, action_type, reason, moderator
            )
            logging.info(f"{action_type.past_tense.capitalize()} {member}")

        await self.moderation_command(
            ctx, members, reason, action, action_type, moderator
        )

    @warn.command()
    @log
    async def show(self, ctx: Context, member: Member):
        db = await Database.get(self.bot)
        with db.session() as session:
            user = db.get_user(member).scalars().first()
            if user is None:
                await ctx.send(f"{member} has no warnings")
                return
            user_id = user.id
            logger.debug(f"{user_id=}")
            query = (
                select(ModerationLinkedAction.linked_id)
                .join(ModerationLinkedAction.moderation_action)
                .where(
                    ModerationAction.user_id == user_id,
                    ModerationAction.action.in_(
                        [ActionType.REMOVE_WARN, ActionType.REMOVE_AUTOWARN, ActionType.REMOVE_AUTOMUTE]
                    ),
                )
            )
            removed = session.execute(query).scalars().all()
            logger.debug(f"{removed=}")
            query = (
                select(ModerationAction)
                .join(ModerationAction.user)
                .where(
                    User.id == user_id,
                    ModerationAction.action.in_([ActionType.WARN, ActionType.AUTOWARN, ActionType.REMOVE_AUTOMUTE]),
                    ModerationAction.id.notin_(removed),
                )
            )
            warnings = session.execute(query).scalars().all()
            logger.debug(f"{warnings=}")

            if any(warnings):

                def format_warning(warning):
                    moderator = warning.moderator.username
                    date = humanize.naturaldate(warning.timestamp)
                    with_reason = (
                        "with no reason given"
                        if warning.reason is None
                        else f"with the reason: {warning.reason}"
                    )
                    return f" • Warning {warning.id}, issued by {moderator} {date} {with_reason}"

                message_parts = ["The following warnings have been issued:"] + [
                    format_warning(w) for w in warnings
                ]
                await ctx.send("\n".join(message_parts))
            else:
                await ctx.send(f"No warnings have been issued for {member.mention}")

    @warn.command()
    @log
    async def remove(
        self, ctx: Context, member: Member, warn_id: int, *, reason: Optional[str]
    ):
        db = await Database.get(self.bot)
        user = db.get_user(member).scalars().one()
        if user is None:
            await ctx.send(f"{member} has no warnings to remove.")
            return
        user_id = user.id
        query = select(ModerationAction).where(
            ModerationAction.id == warn_id,
            ModerationAction.action.in_([ActionType.WARN, ActionType.AUTOWARN]),
            ModerationAction.user_id == user_id,
        )
        with db.session() as session:
            result = session.execute(query).scalars().first()

        if result is not None:
            action_type = {
                ActionType.WARN: ActionType.REMOVE_WARN,
                ActionType.AUTOWARN: ActionType.REMOVE_AUTOWARN,
            }[result.action]
            await self.add_moderation_history_item(
                member, action_type, reason, ctx.author, linked_action_id=result.id
            )
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❌")

    @command(cls=Greedy1Command)
    @log
    async def kick(
        self,
        ctx: Context,
        members: Greedy[Member],
        *,
        reason: Optional[str],
    ):
        moderator = ctx.author
        action_type = ActionType.KICK

        async def action(member):
            await member.kick(reason=reason)
            await self.add_moderation_history_item(
                member, action_type, reason, moderator
            )
            logging.info(f"{action_type.past_tense.capitalize()} {member}")

        await self.moderation_command(
            ctx, members, reason, action, action_type, moderator
        )

    @command(cls=Greedy1Command)
    @log
    async def tempban(
        self,
        ctx: Context,
        members: Greedy[Member],
        until: DateTimeConverter,
        delete_message_days: Optional[int] = 0,
        *,
        reason: Optional[str],
    ):
        moderator = ctx.author
        action_type = ActionType.TEMPBAN

        async def action(member):
            await member.ban(reason=reason, delete_message_days=delete_message_days)
            # noinspection PyTypeChecker
            await self.add_moderation_history_item(
                member, action_type, reason, ctx.author, until
            )
            logging.info(f"{action_type.past_tense.capitalize()} {member}")

        await self.moderation_command(
            ctx, members, reason, action, action_type, moderator, until
        )

    @command(cls=Greedy1Command)
    @log
    async def ban(
        self,
        ctx: Context,
        members: Greedy[Member],
        delete_message_days: Optional[int] = 0,
        *,
        reason: Optional[str],
    ):
        moderator = ctx.author
        action_type = ActionType.BAN

        async def action(member):
            await member.ban(reason=reason, delete_message_days=delete_message_days)
            await self.add_moderation_history_item(
                member, action_type, reason, ctx.author
            )
            logging.info(f"{action_type.past_tense.capitalize()} {member}")

        await self.moderation_command(
            ctx, members, reason, action, action_type, moderator
        )

    @command(cls=Greedy1Command)
    @log
    async def unban(self, ctx: Context, users: Greedy[DiscordUser], *, reason: Optional[str]):
        moderator = ctx.author
        action_type = ActionType.UNBAN

        async def action(user):
            await self.guild.unban(user, reason=reason)
            await self.add_moderation_history_item(user, action_type, reason, moderator)
            logging.info(f"{action_type.past_tense.capitalize()} {user}")

        await self.moderation_command(
            ctx, users, reason, action, action_type, moderator
        )


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
