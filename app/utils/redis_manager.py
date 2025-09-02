# app/utils/redis_manager.py
import asyncio
from typing import Optional
from redis.asyncio import Redis, from_url
from app.core.config import conf
from app.core.logger import get_logger

logger = get_logger()

class RedisManager:
    _client: Optional[Redis] = None

    @classmethod
    async def init(cls):
        if cls._client:
            return cls._client
        cls._client = from_url(conf.redis_url, decode_responses=False)
        try:
            await cls._client.ping()
            logger.info("RedisManager: initialized")
        except Exception:
            logger.exception("RedisManager: failed to ping redis")
            raise
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            try:
                await cls._client.close()
            except Exception:
                logger.exception("RedisManager close failed")
            cls._client = None
            logger.info("RedisManager: closed")

    @classmethod
    def client(cls) -> Optional[Redis]:
        return cls._client
