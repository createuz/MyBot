# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import conf
from app.core.logger import get_logger

logger = get_logger()
Base = declarative_base()

# Read pooling config from conf (provide sensible defaults)
# conf should expose db_pool_min, db_pool_max, use_pgbouncer (bool)
min_pool = int(getattr(conf, "db_pool_min", 5))
max_overflow = int(getattr(conf, "db_pool_max", 20))
use_pgbouncer = bool(getattr(conf, "use_pgbouncer", False))

# If using PgBouncer in transaction pooling mode -> use NullPool to avoid SQLAlchemy holding
# server-side connections across transactions.
if use_pgbouncer:
    poolclass = NullPool
    logger.info("Using NullPool because use_pgbouncer=True (recommended for transaction pooling)")
    engine = create_async_engine(
        conf.database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        poolclass=poolclass,
    )
else:
    # Normal SQLAlchemy pooling (QueuePool) with pool_size and max_overflow
    engine = create_async_engine(
        conf.database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=min_pool,
        max_overflow=max_overflow,
    )

# Session maker
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def dispose_db():
    await engine.dispose()
    logger.info("Database disposed")
