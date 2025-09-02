# app/utils/redis_manager.py
from redis.asyncio import from_url, Redis

from app.core.config import conf
from app.core.logger import get_logger

logger = get_logger()


class RedisManager:
    _client: Redis | None = None

    @classmethod
    async def init(cls):
        if cls._client:
            return cls._client
        url = conf.redis.url_or_build()
        cls._client = from_url(url, decode_responses=False)
        try:
            await cls._client.ping()
            logger.info("Redis client initialized")
        except Exception:
            logger.exception("Redis init failed")
            raise
        return cls._client

    @classmethod
    def client(cls) -> Redis | None:
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            try:
                await cls._client.close()
            except Exception:
                logger.exception("Redis close failed")
            cls._client = None
            logger.info("Redis closed")
