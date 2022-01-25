"""Create moderation actions tables

Revision ID: 91a4a0ccfc81
Revises: 63a018fe1c9c
Create Date: 2021-06-13 20:45:00.110033

"""
import enum

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Text

from alembic import op

# revision identifiers, used by Alembic.

revision = "91a4a0ccfc81"
down_revision = "63a018fe1c9c"
branch_labels = None
depends_on = None


@enum.unique
class ActionType(enum.Enum):
    """Enum at the time the migration was written"""

    TEMPMUTE = enum.auto()
    TIMEOUT = enum.auto()
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


def upgrade():
    op.create_table(
        "moderation_actions",
        Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
        Column(
            "timestamp", DateTime, nullable=False, default=sa.func.current_timestamp()
        ),
        Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("moderator_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("action", Enum(ActionType), nullable=False),
        Column("reason", Text, nullable=True),
    )

    op.create_table(
        "moderation_temporary_actions",
        Column(
            "id",
            Integer,
            ForeignKey("moderation_actions.id"),
            primary_key=True,
            nullable=False,
        ),
        Column("until", DateTime, nullable=False),
        Column("completed", Boolean, nullable=False, default=False),
    )

    op.create_table(
        "moderation_linked_actions",
        Column(
            "id",
            Integer,
            ForeignKey("moderation_actions.id"),
            primary_key=True,
            nullable=False,
        ),
        Column(
            "linked_id",
            Integer,
            ForeignKey("moderation_actions.id"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("moderation_temporary_actions")
    op.drop_table("moderation_linked_actions")
    op.drop_table("moderation_actions")
    bind = op.get_bind()
    Enum(ActionType).drop(bind)
