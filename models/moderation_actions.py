import enum

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from models.models import Base, model_repr

__all__ = [
    "ActionType",
    "ModerationAction",
    "ModerationLinkedAction",
    "ModerationTemporaryAction",
]


@enum.unique
class ActionType(enum.Enum):
    def __repr__(self):
        return f"<{type(self).__name__}.{self.name}:{self.value}>"

    def __str__(self):
        return f"{self.name}"

    @property
    def past_tense(self):
        mapping = {
            ActionType.TEMPMUTE: "tempmuted",
            ActionType.MUTE: "muted",
            ActionType.UNMUTE: "unmuted",
            ActionType.WARN: "warned",
            ActionType.REMOVE_WARN: "warning removed",
            ActionType.AUTOMUTE: "automuted",
            ActionType.REMOVE_AUTOMUTE: "automute removed",
            ActionType.KICK: "kicked",
            ActionType.TEMPBAN: "tempbanned",
            ActionType.BAN: "banned",
            ActionType.UNBAN: "unbanned",
        }
        return mapping[self]

    @property
    def emoji(self):
        mapping = {
            ActionType.TEMPMUTE: ":speaker:",
            ActionType.MUTE: ":speaker:",
            ActionType.UNMUTE: ":speaker:",
            ActionType.WARN: ":warning:",
            ActionType.REMOVE_WARN: ":warning:",
            ActionType.AUTOMUTE: ":speaker:",
            ActionType.REMOVE_AUTOMUTE: ":speaker:",
            ActionType.KICK: ":door:",
            ActionType.TEMPBAN: ":hammer:",
            ActionType.BAN: ":hammer:",
            ActionType.UNBAN: ":dove:",
        }
        return mapping[self]

    TEMPMUTE = enum.auto()
    MUTE = enum.auto()
    UNMUTE = enum.auto()
    WARN = enum.auto()
    REMOVE_WARN = enum.auto()
    AUTOWARN = enum.auto()
    REMOVE_AUTOWARN = enum.auto()
    AUTOMUTE = enum.auto()
    REMOVE_AUTOMUTE = enum.auto()
    KICK = enum.auto()
    TEMPBAN = enum.auto()
    BAN = enum.auto()
    UNBAN = enum.auto()


@model_repr
class ModerationAction(Base):
    __tablename__ = "moderation_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=sa.func.current_timestamp())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(Enum(ActionType), nullable=False)
    reason = Column(Text, nullable=True)

    user = relationship(
        "User",
        back_populates="moderation_actions",
        uselist=False,
        foreign_keys=[user_id],
        primaryjoin="User.id == ModerationAction.user_id",
    )

    moderator = relationship(
        "User",
        uselist=False,
        foreign_keys=[moderator_id],
        primaryjoin="User.id == ModerationAction.moderator_id",
    )

    linked_to = relationship(
        "ModerationLinkedAction",
        back_populates="moderation_action",
        primaryjoin="ModerationAction.id == ModerationLinkedAction.id",
    )

    linked_from = relationship(
        "ModerationLinkedAction",
        back_populates="linked_moderation_action",
        primaryjoin="ModerationAction.id == ModerationLinkedAction.linked_id",
    )


@model_repr
class ModerationTemporaryAction(Base):
    __tablename__ = "moderation_temporary_actions"

    id = Column(
        Integer, ForeignKey("moderation_actions.id"), primary_key=True, nullable=False
    )
    until = Column(DateTime, nullable=False)
    completed = Column(Boolean, nullable=False, default=False)

    moderation_action = relationship("ModerationAction")


@model_repr
class ModerationLinkedAction(Base):
    __tablename__ = "moderation_linked_actions"

    id = Column(
        Integer, ForeignKey("moderation_actions.id"), primary_key=True, nullable=False
    )
    linked_id = Column(Integer, ForeignKey("moderation_actions.id"), nullable=False)

    moderation_action = relationship(
        "ModerationAction",
        foreign_keys=[id],
        back_populates="linked_to",
        primaryjoin="ModerationLinkedAction.id == ModerationAction.id",
    )
    linked_moderation_action = relationship(
        "ModerationAction",
        foreign_keys=[linked_id],
        back_populates="linked_from",
        primaryjoin="ModerationLinkedAction.linked_id == ModerationAction.id",
    )
