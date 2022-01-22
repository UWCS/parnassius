from __future__ import annotations

import logging

from discord.ext.commands import Bot, Cog
from sqlalchemy import create_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from config import CONFIG
from models import User
from utils.logging import log_func

__all__ = ["Database"]


logger = logging.getLogger("parnassius.cogs.database")
log = log_func(logger)


class Database(Cog):
    @log
    def __init__(self, bot: Bot):
        self.bot = bot
        self._engine = None

    @property
    @log
    def engine(self):
        if self._engine is None:
            logger.info("Creating database engine")
            connection = CONFIG["database"]["connection"].get(str)
            self._engine = create_engine(connection)
        return self._engine

    @engine.deleter
    @log
    def engine(self):
        logger.info("Disposing database engine")
        self._engine.dispose()
        self._engine = None

    @property
    @log
    def session(self):
        return sessionmaker(self.engine)

    @classmethod
    @log
    async def get(cls, bot: Bot) -> Database:
        await bot.wait_until_ready()
        return bot.get_cog(cls.__name__)

    @log
    def get_user(self, ctx: {id: int}) -> User:
        with self.session() as session:
            return session.execute(select(User).where(User.discord_id == ctx.id))

    @log
    def get_user_from_id(self, id_: int) -> User:
        with self.session() as session:
            return session.execute(select(User).where(User.discord_id == id_))


@log
def setup(bot: Bot):
    bot.add_cog(Database(bot))
