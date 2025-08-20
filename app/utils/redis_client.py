# app/utils/redis_client.py
from redis.asyncio import Redis

from app.core.config import conf
from app.core.logger import get_logger

_redis = None
logger = get_logger()


async def init_redis():
    global _redis
    if _redis is None:
        _redis = Redis.from_url(conf.redis_url, decode_responses=False)
        await _redis.ping()
        logger.info("Redis client initialized")
    return _redis


async def get_redis():
    if _redis is None:
        return await init_redis()
    return _redis


async def close_redis():
    global _redis
    if _redis:
        try:
            await _redis.close()
        except Exception:
            logger.warning("Redis close failed")
        _redis = None
