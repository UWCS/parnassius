from sqlalchemy import BigInteger, Column, Integer, String
from sqlalchemy.orm import relationship

from models.models import Base, model_repr

__all__ = ("User",)


@model_repr
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    discord_id = Column(BigInteger, nullable=False)
    # Max username length is 32
    # + 1 character for #
    # + 4 characters for discriminator
    username = Column(String(length=37), nullable=False)

    moderation_actions = relationship(
        "ModerationAction",
        back_populates="user",
        primaryjoin="User.id == ModerationAction.user_id",
    )
