import enum

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from models.models import Base, model_repr

__all__ = (
    "ActionType",
    "ModerationAction",
    "ModerationLinkedAction",
    "ModerationTemporaryAction",
)


@enum.unique
class ActionType(enum.Enum):
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
    linked_action = Column(Integer, ForeignKey("moderation_actions.id"), nullable=False)

    moderation_action = relationship(
        "ModerationAction",
        foreign_keys=[id],
        primaryjoin="ModerationLinkedAction.id == ModerationAction.id",
    )
    linked_moderation_action = relationship(
        "ModerationAction",
        foreign_keys=[linked_action],
        primaryjoin="ModerationLinkedAction.linked_action == ModerationAction.id",
    )