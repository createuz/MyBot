# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
# from sqlalchemy.orm import declarative_base
#
# from app.core.config import conf
# from app.core.logger import logger
#
# Base = declarative_base()
#
# engine = create_async_engine(
#     conf.database_url,
#     echo=False,
#     future=True,
#     pool_pre_ping=True,
#     pool_size=conf.db_pool_min,
#     max_overflow=conf.db_pool_max,
# )
#
# AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
#
#
# async def init_db():
#     # development only: create tables (in prod use alembic migrations)
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     logger.info("✅ DB initialized (create_all)")
#
#
# async def dispose_db():
#     await engine.dispose()
#     logger.info("🛑 DB engine disposed")
# app/db/session.py
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from core.config import conf
from core.logger import get_logger

logger = get_logger()

Base = declarative_base()

def async_engine_builder(url: str):
    return create_async_engine(
        url,
        future=True,
        echo=True,
        pool_pre_ping=True,
        pool_size=conf.c,
        max_overflow=conf.db_pool_max,
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
