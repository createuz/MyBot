# app/utils/redis_client.py
from redis.asyncio import Redis

from core.config import conf
from core.logger import get_logger

logger = get_logger()
_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = Redis.from_url(conf.redis_url, decode_responses=True)
        logger.info("Redis client initialized")
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
        logger.info("Redis closed")
