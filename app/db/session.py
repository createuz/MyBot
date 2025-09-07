# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import conf
from app.core.logger import get_logger

logger = get_logger()
Base = declarative_base()

if conf.db.use_pgbouncer:
    poolclass = NullPool
    logger.info("Using NullPool because use_pgbouncer=True (recommended for transaction pooling)")
    _engine = create_async_engine(
        conf.db.sqlalchemy_url(),
        echo=False,
        future=True,
        pool_pre_ping=True,
        poolclass=poolclass,
    )
else:
    _engine = create_async_engine(
        conf.db.sqlalchemy_url(),
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=conf.db.pool_min,
        max_overflow=conf.db.pool_max,
    )

AsyncSessionLocal = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def init_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def dispose_db():
    await _engine.dispose()
    logger.info("Database disposed")
