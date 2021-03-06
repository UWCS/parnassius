from __future__ import annotations

import logging
from collections import Mapping
from dataclasses import asdict, astuple, dataclass
from datetime import datetime, timedelta
from enum import Enum, auto, unique
from typing import Optional, Union

from confuse import Subview
from discord import (
    AuditLogAction,
    AuditLogEntry,
    CategoryChannel,
    Embed,
    Member,
    Message,
    StageChannel,
    TextChannel,
    User,
    VoiceChannel,
    VoiceState,
)
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Cog
from humanize import precisedelta

from config import CONFIG
from utils.logging import log_func

__all__ = ["Logging"]

logger = logging.getLogger("parnassius.cogs.logging")
log = log_func(logger)


class Logging(Cog):
    @log
    def __init__(self, bot: Bot):
        self.bot = bot
        self.config = CONFIG["discord_logging"]
        self.channels = self.config["channels"]

    @classmethod
    @log
    async def get(cls, bot: Bot) -> Logging:
        await bot.wait_until_ready()
        return bot.get_cog(cls.__name__)

    @log
    async def log_event(
        self,
        channel,
        user: Optional[Union[User, Member]],
        title,
        description,
        colour,
        thumbnail_url=None,
    ):
        embed = Embed(title=title, description=description, colour=colour)
        if user:
            embed.set_author(
                name=str(user),
                url=Embed.Empty,
                icon_url=user.avatar_url,
            )
            embed.set_footer(text=self.config["footer"].get(str).format(id=user.id))
        embed.timestamp = datetime.utcnow()
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        await channel.send(embed=embed)

    @dataclass(frozen=True)
    class ConfigSection(Mapping):
        channel_id: int
        title: str
        description: str
        colour: int

        @log
        def __iter__(self):
            return iter(self.astuple())

        @log
        def __getitem__(self, keys):
            return iter(getattr(self, k) for k in keys)

        @log
        def __len__(self) -> int:
            return len(self.astuple())

        @log
        def asdict(self):
            return asdict(self)

        @log
        def astuple(self):
            return astuple(self)

    @log
    async def get_config_parts(self, config_section: Subview) -> Logging.ConfigSection:
        channel_id = self.channels[config_section["channel"].get(str)].get(int)
        title = config_section["head"].get(str)
        description = config_section["desc"].get(str)
        colour = config_section["colour"].get(int)
        return Logging.ConfigSection(channel_id, title, description, colour)

    @log
    async def get_config_parts_from_name(self, name: str) -> Logging.ConfigSection:
        return await self.get_config_parts(self.config[name])

    @staticmethod
    @log
    async def try_audit_entry(action, audit_logs, predicate) -> Optional[AuditLogEntry]:
        before = datetime.utcnow()
        # Padding to allow for slow execution
        after = before - timedelta(seconds=5)
        # oldest_first = false to work from newest entries first
        # It's likely that the most recent entry of the audit logs will be the one the user is looking for
        # so it makes sense to search in that order
        logs = audit_logs(action=action, after=after, before=before, oldest_first=False)
        async for entry in logs:
            # guild.audit_logs was retrieving logs from outside the specified range.
            # This checks that the range is enforced.
            if entry.created_at < after:
                break
            if predicate(entry):
                return entry

    @unique
    class ChannelType(Enum):
        TEXT = auto()
        VOICE = auto()
        CATEGORY = auto()
        STAGE = auto()

        @property
        def str_mapping(self):
            return {
                self.TEXT: "text",
                self.VOICE: "voice",
                self.CATEGORY: "category",
                self.STAGE: "stage",
            }

        def __str__(self):
            return self.str_mapping[self]

    @log
    def get_channel_type(self, channel: GuildChannel) -> Logging.ChannelType:
        if isinstance(channel, TextChannel):
            return self.ChannelType.TEXT
        elif isinstance(channel, VoiceChannel):
            return self.ChannelType.VOICE
        elif isinstance(channel, CategoryChannel):
            return self.ChannelType.CATEGORY
        elif isinstance(channel, StageChannel):
            return self.ChannelType.STAGE

    @Cog.listener()
    @log
    async def on_member_join(self, member: Member):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "member_join"
        )

        channel = self.bot.get_channel(channel_id)
        age = datetime.now() - member.created_at
        warning = (
            "**:warning: NEW ACCOUNT! :warning:**" if age < timedelta(days=7) else ""
        )
        description = description.format(
            ping=member.mention,
            age=precisedelta(age, minimum_unit="hours"),
            warning=warning,
        )
        await self.log_event(channel, member, title, description, colour)

    @Cog.listener()
    @log
    async def on_member_remove(self, member: Member):
        logs = await self.try_audit_entry(
            AuditLogAction.kick, member.guild.audit_logs, lambda e: e.target == member
        )
        was_kicked = logs is not None

        if was_kicked:
            await self.on_member_kick(member, logs)
        else:
            await self.on_member_leave(member)

    @log
    async def on_member_leave(self, member: Member):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "member_leave"
        )

        channel = self.bot.get_channel(channel_id)
        age = datetime.now() - member.joined_at
        description = description.format(
            ping=member.mention, age=precisedelta(age, minimum_unit="hours")
        )
        await self.log_event(channel, member, title, description, colour)

    @log
    async def on_member_kick(self, member: Member, logs: AuditLogEntry):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "member_kick"
        )

        channel = self.bot.get_channel(channel_id)
        source = logs.user.mention if logs.target == member else None
        reason = logs.reason if logs.target == member else None
        description = description.format(user=str(member), source=source, reason=reason)

        await self.log_event(channel, member, title, description, colour)

    @Cog.listener()
    @log
    async def on_member_ban(self, guild, user: Union[User, Member]):
        # If the person was in the guild at the time of the ban, this will be passed a Member
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "member_ban"
        )

        channel = self.bot.get_channel(channel_id)
        logs = await guild.audit_logs(limit=1, action=AuditLogAction.ban).next()
        source = logs.user.mention if logs.target == user else None
        reason = logs.reason if logs.target == user else None
        description = description.format(user=str(user), source=source, reason=reason)
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    @log
    async def on_member_unban(self, guild, user: User):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "user_unban"
        )

        channel = self.bot.get_channel(channel_id)
        logs = await guild.audit_logs(limit=1, action=AuditLogAction.unban).next()
        source = logs.user.mention if logs.target == user else None
        description = description.format(user=str(user), source=source)
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    @log
    async def on_member_update(self, before: Member, after: Member):
        if before.nick != after.nick:
            await self.on_member_nick(before, after)
        if any(set(after.roles) - set(before.roles)):
            await self.on_member_role(before, after)
        if any(set(before.roles) - set(after.roles)):
            await self.on_member_derole(before, after)
        if before.pending and not after.pending:
            pass

    @log
    async def on_member_nick(self, before: Member, after: Member):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "nickname"
        )

        channel = self.bot.get_channel(channel_id)
        description = description.format(before=before.nick, after=after.nick)
        await self.log_event(channel, before, title, description, colour)

    @log
    async def on_member_role(self, before: Member, after: Member):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "role_add"
        )

        channel = self.bot.get_channel(channel_id)
        roles = [role.mention for role in after.roles if role not in before.roles]
        title = title.format(plural="" if len(roles) == 1 else "s")
        description = description.format(roles=", ".join(roles))
        await self.log_event(channel, before, title, description, colour)

    @log
    async def on_member_derole(self, before: Member, after: Member):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "role_remove"
        )

        channel = self.bot.get_channel(channel_id)
        roles = [role.mention for role in before.roles if role not in after.roles]
        title = title.format(plural="" if len(roles) == 1 else "s")
        description = description.format(roles=", ".join(roles))
        await self.log_event(channel, before, title, description, colour)

    @log
    async def on_member_cease_pending(self, _: Member, after: Member):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "member_pending"
        )

        description = description.format(ping=after.mention)
        channel = self.bot.get_channel(channel_id)
        await self.log_event(channel, after, title, description, colour)

    @Cog.listener()
    @log
    async def on_user_update(self, before: User, after: User):
        if before.name != after.name:
            await self.on_user_name(before, after)
        if before.discriminator != after.discriminator:
            await self.on_user_discriminator(before, after)
        if before.avatar_url != after.avatar_url:
            await self.on_user_avatar(before, after)

    @log
    async def on_user_name(self, before: User, after: User):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "member_username"
        )

        channel = self.bot.get_channel(channel_id)
        description = description.format(before=before.name, after=after.name)
        await self.log_event(channel, after, title, description, colour)

    @log
    async def on_user_discriminator(self, before: User, after: User):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "member_discriminator"
        )

        channel = self.bot.get_channel(channel_id)
        description = description.format(
            before=before.discriminator, after=after.discriminator
        )
        await self.log_event(channel, after, title, description, colour)

    @log
    async def on_user_avatar(self, _: User, after: User):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "member_avatar"
        )

        channel = self.bot.get_channel(channel_id)
        description = description.format(ping=after.mention)
        await self.log_event(
            channel, after, title, description, colour, thumbnail_url=after.avatar_url
        )

    @Cog.listener()
    @log
    async def on_message_edit(self, before: Message, after: Message):
        if before.content == after.content:
            return

        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "message_edit"
        )
        channel = self.bot.get_channel(channel_id)

        title = title.format(channel=f"#{before.channel}")
        description = description.format(
            before=before.content, after=after.content, link=after.jump_url
        )
        await self.log_event(channel, before.author, title, description, colour)

    @Cog.listener()
    @log
    async def on_raw_message_edit(self, payload):
        if payload.cached_message is not None:
            # Cached messages are handled by the event above, `on_message_edit`
            return

        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "message_edit_uncached"
        )
        channel = self.bot.get_channel(channel_id)
        message = await self.bot.get_channel(payload.channel_id).fetch_message(
            payload.message_id
        )
        title = title.format(channel=f"#{channel}")
        description = description.format(after=message.content, link=message.jump_url)
        await self.log_event(channel, message.author, title, description, colour)

    @Cog.listener()
    @log
    async def on_message_delete(self, message: Message):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "message_delete"
        )

        channel = self.bot.get_channel(channel_id)
        title = title.format(channel=message.channel)
        description = description.format(
            ping=message.author.mention, message=message.content
        )
        await self.log_event(channel, message.author, title, description, colour)

    @Cog.listener()
    @log
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        if before.channel is None and after.channel is not None:
            await self.on_voice_join(member, before, after)
        elif before.channel is not None and after.channel is None:
            await self.on_voice_leave(member, before, after)
        elif before.channel != after.channel:
            await self.on_voice_move(member, before, after)

    @log
    async def on_voice_join(self, member: Member, _: VoiceState, after: VoiceState):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "voice_join"
        )

        channel = self.bot.get_channel(channel_id)
        description = description.format(
            ping=member.mention, channel=after.channel.mention
        )
        await self.log_event(channel, member, title, description, colour)

    @log
    async def on_voice_leave(self, member: Member, before: VoiceState, _: VoiceState):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "voice_leave"
        )

        channel = self.bot.get_channel(channel_id)
        description = description.format(
            ping=member.mention, channel=before.channel.mention
        )
        await self.log_event(channel, member, title, description, colour)

    @log
    async def on_voice_move(self, member: Member, before, after):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "voice_move"
        )

        channel = self.bot.get_channel(channel_id)
        description = description.format(
            before=before.channel.mention, after=after.channel.mention
        )
        await self.log_event(channel, member, title, description, colour)

    @Cog.listener()
    @log
    async def on_guild_channel_delete(self, channel: GuildChannel):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "channel_delete"
        )

        entry = await self.try_audit_entry(
            AuditLogAction.channel_delete,
            channel.guild.audit_logs,
            lambda e: e.target.id == channel.id,
        )

        channel_type = self.get_channel_type(channel)
        user: User = entry and entry.user
        name = self.format_channel_name(channel, channel_type)
        title = title.format(type=str(channel_type).capitalize())
        description = description.format(
            ping=user.mention if user else "Unknown",
            type=channel_type,
            name=name,
            category=channel.category,
        )
        logging_channel = self.bot.get_channel(channel_id)
        await self.log_event(logging_channel, user, title, description, colour)

    @Cog.listener()
    @log
    async def on_guild_channel_create(self, channel: GuildChannel):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "channel_create"
        )

        entry = await self.try_audit_entry(
            AuditLogAction.channel_create,
            channel.guild.audit_logs,
            lambda e: e.target == channel,
        )

        channel_type = self.get_channel_type(channel)
        user: User = entry and entry.user
        # This is a not a mention because mentions turn into #deleted-channel if the channel is deleted
        name = self.format_channel_name(channel, channel_type)
        title = title.format(type=str(channel_type).capitalize())
        description = description.format(
            ping=user.mention if user else "Unknown",
            type=channel_type,
            name=name,
            category=channel.category,
        )
        logging_channel = self.bot.get_channel(channel_id)
        await self.log_event(logging_channel, user, title, description, colour)

    @Cog.listener()
    @log
    async def on_guild_channel_update(self, before: GuildChannel, after: GuildChannel):
        channel_id, title, description, colour = await self.get_config_parts_from_name(
            "channel_update"
        )
        entry = await self.try_audit_entry(
            AuditLogAction.channel_update,
            after.guild.audit_logs,
            lambda e: e.target == before or e.target == after,
        )
        channel_type = self.get_channel_type(after)
        name = self.format_channel_name(after, channel_type)
        user: User = entry and entry.user
        changes = ""

        if before.category != after.category:
            changes += f"Category ~~{before.category}~~ {after.category}\n"
        if before.changed_roles != after.changed_roles:
            changes += f"Roles with overridden permissions ~~{before.changed_roles}~~ {after.changed_roles}\n"
        if before.name != after.name:
            before_name = self.format_channel_name(before, channel_type)
            changes += f"Name ~~{before_name}~~ {name}\n"
        if before.overwrites != after.overwrites:
            changes += (
                f"Permission overwrites ~~{before.overwrites}~~ {after.overwrites}\n"
            )
        if before.permissions_synced != after.permissions_synced:
            changes += f"Permissions synced ~~{before.permissions_synced}~~ {after.permissions_synced}\n"

        title = title.format(type=str(channel_type).capitalize())
        description = description.format(
            ping=user.mention if user else "Unknown",
            type=channel_type,
            name=name,
            category=after.category,
            changes=changes,
        )

        logging_channel = self.bot.get_channel(channel_id)
        await self.log_event(logging_channel, user, title, description, colour)

    @log
    def format_channel_name(
        self, channel: GuildChannel, channel_type: ChannelType
    ) -> str:
        return (
            f"#{channel.name}"
            if channel_type == self.ChannelType.TEXT
            else channel.name
        )


@log
def setup(bot: Bot):
    bot.add_cog(Logging(bot))
