"""Create users table

Revision ID: 63a018fe1c9c
Revises: 
Create Date: 2021-06-13 19:56:00.090344

"""
from alembic import op
from sqlalchemy import BigInteger, Column, Integer, String

# revision identifiers, used by Alembic.
revision = "63a018fe1c9c"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
        Column("discord_id", BigInteger, nullable=False),
        # Max username length is 32
        # + 1 character for #
        # + 4 characters for discriminator
        Column("username", String(length=37), nullable=False),
    )


def downgrade():
    op.drop_table("users")
