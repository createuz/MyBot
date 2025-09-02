# app/utils/user_cache.py
from typing import Optional

from sqlalchemy import select

from app.core.logger import get_logger
from app.db.models import User
from app.utils.redis_manager import RedisManager

logger = get_logger()
CACHE_TTL = 7 * 24 * 3600  # 7 days


async def get_lang_cache_then_db(session, chat_id: int) -> Optional[str]:
    """
    1) Try redis (confirmed lang)
    2) If miss -> query DB: if user exists and language is not None -> set redis and return
    3) else return None (means ask language)
    """
    # try redis
    try:
        val = await RedisManager.get(f"user:{chat_id}:lang")
        if val:
            logger.debug("cache hit redis for %s -> %s", chat_id, val)
            return val
    except Exception:
        logger.warning("get_lang: redis read failed for %s", chat_id)

    # redis miss -> DB
    try:
        result = await session.execute(select(User).where(User.chat_id == chat_id))
        user = result.scalars().first()
        if not user:
            logger.debug("get_lang: DB miss for %s", chat_id)
            return None
        if user.language:
            # confirmed in DB, push to redis (best-effort)
            try:
                await RedisManager.set(f"user:{chat_id}:lang", user.language, ex=CACHE_TTL)
            except Exception:
                logger.warning("get_lang: redis set failed")
            return user.language
        # user exists but language NULL -> ask language
        logger.debug("get_lang: user exists but language NULL for %s", chat_id)
        return None
    except Exception as e:
        logger.exception("get_lang: DB read error %s: %s", chat_id, e)
        return None
