from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from core import conf
from core.logger import get_logger

logger = get_logger()

Base = declarative_base()


def async_engine_builder(url: str):
    return create_async_engine(
        url,
        future=True,
        echo=True,
        pool_pre_ping=True,
        pool_size=int(conf.bot.db_pool_min),
        max_overflow=int(conf.bot.db_pool_max),
    )


class AsyncDatabase:
    def __init__(self, db_url: str):
        self._engine = async_engine_builder(db_url)
        self._SessionMaker = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession,
        )

    @asynccontextmanager
    async def get_session(self):
        async with self._SessionMaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def init(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("DB init done")

    async def dispose(self):
        await self._engine.dispose()
        logger.info("DB disposed")


# single global instance (imported where needed)
db = AsyncDatabase(db_url=str(conf.db.build_db_url()))
