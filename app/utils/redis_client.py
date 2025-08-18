# app/utils/redis_client.py
from redis.asyncio import Redis

from app.core.config import conf
from app.core.logger import get_logger

logger = get_logger()
_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = Redis.from_url(conf.bot.reds_url, decode_responses=True)
        logger.info("Redis client initialized")
    return _redis


async def close_redis():
    global _redis
    if _redis:
        try:
            await _redis.close()
            logger.info("Redis closed")
        except Exception as e:
            logger.warning(f"Redis close failed: {e}")
        _redis = None
