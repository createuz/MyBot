# app/utils/redis_client.py
from typing import Optional

import redis.asyncio as redis

from app.core import conf
from app.core.logger import get_logger

logger = get_logger()

_redis: Optional[redis.Redis] = None


async def init_redis() -> Optional[redis.Redis]:
    global _redis
    if _redis:
        return _redis
    try:
        _redis = redis.from_url(str(conf.redis_url))
        await _redis.ping()
        logger.info("Redis initialized")
        return _redis
    except Exception as e:
        logger.warning("Redis init failed: %s", e)
        _redis = None
        return None


async def get_redis() -> Optional[redis.Redis]:
    if _redis:
        return _redis
    return await init_redis()


# small helpers: return None / False on failure (handlers stay simple)
async def redis_get(key: str) -> Optional[str]:
    client = await get_redis()
    if not client:
        return None
    try:
        v = await client.get(key)
        if v is None:
            return None
        if isinstance(v, bytes):
            return v.decode()
        return str(v)
    except Exception as e:
        logger.warning("redis_get error %s: %s", key, e)
        return None


async def redis_set(key: str, value: str, ex: Optional[int] = None) -> bool:
    client = await get_redis()
    if not client:
        return False
    try:
        await client.set(key, value, ex=ex)
        return True
    except Exception as e:
        logger.warning("redis_set error %s: %s", key, e)
        return False


async def redis_delete(*keys: str) -> bool:
    client = await get_redis()
    if not client:
        return False
    try:
        await client.delete(*keys)
        return True
    except Exception as e:
        logger.warning("redis_delete error %s: %s", keys, e)
        return False

async def close_redis():
    global _redis
    if _redis:
        try:
            await _redis.close()
        except Exception:
            logger.warning("Redis close failed")
        _redis = None