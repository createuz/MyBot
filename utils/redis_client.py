# app/utils/redis_client.py
from redis.asyncio import Redis

from core.config import conf
from core.logger import get_logger

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
        await _redis.close()
        _redis = None
        logger.info("Redis closed")

# # app/utils/redis_client.py
# import aioredis
# from app.core.config import conf
# from app.core.logger import get_logger
#
# logger = get_logger()
# _redis = None
#
# async def get_redis():
#     global _redis
#     if _redis is None:
#         _redis = aioredis.from_url(conf.redis_url, decode_responses=True)
#         logger.info("Redis client initialized")
#     return _redis
#
# async def safe_get(key: str):
#     r = await get_redis()
#     try:
#         return await r.get(key)
#     except Exception as e:
#         logger.warning(f"Redis GET error for {key}: {e}")
#         return None
#
# async def safe_set(key: str, value, ex: int | None = None):
#     r = await get_redis()
#     try:
#         await r.set(key, value, ex=ex)
#         return True
#     except Exception as e:
#         logger.warning(f"Redis SET error for {key}: {e}")
#         return False
