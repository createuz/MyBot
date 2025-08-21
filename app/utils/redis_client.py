# app/utils/redis_manager.py
from typing import Optional
import asyncio
import redis.asyncio as redis
from app.core.config import conf  # or get_settings()
from app.core.logger import get_logger

logger = get_logger()

class RedisManager:
    _client: Optional[redis.Redis] = None

    @classmethod
    async def init(cls) -> Optional[redis.Redis]:
        if cls._client:
            return cls._client
        url = str(conf.redis_url)
        try:
            cls._client = redis.from_url(url)
            await cls._client.ping()
            logger.info("RedisManager: initialized")
            return cls._client
        except Exception as e:
            logger.warning("RedisManager: init failed: %s", e)
            cls._client = None
            return None

    @classmethod
    def client(cls) -> Optional[redis.Redis]:
        return cls._client

    @classmethod
    async def get(cls, key: str) -> Optional[str]:
        c = cls.client() or await cls.init()
        if not c:
            return None
        v = await c.get(key)
        if v is None:
            return None
        return v.decode() if isinstance(v, bytes) else str(v)

    @classmethod
    async def set(cls, key: str, val: str, ex: int = None) -> bool:
        c = cls.client() or await cls.init()
        if not c:
            return False
        try:
            await c.set(key, val, ex=ex)
            return True
        except Exception as e:
            logger.warning("RedisManager.set failed %s: %s", key, e)
            return False

    @classmethod
    async def delete(cls, *keys: str) -> bool:
        c = cls.client() or await cls.init()
        if not c:
            return False
        try:
            await c.delete(*keys)
            return True
        except Exception as e:
            logger.warning("RedisManager.delete failed %s: %s", keys, e)
            return False

    @classmethod
    async def close(cls):
        if cls._client:
            try:
                await cls._client.close()
            except Exception:
                logger.exception("RedisManager.close failed")
            cls._client = None
