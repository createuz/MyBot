# app/utils/user_service.py
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.logger import get_logger
from app.db.models import User

logger = get_logger()
CACHE_TTL = 7 * 24 * 3600  # 7 days


async def db_get_lang(session, chat_id: int) -> Optional[str]:
    try:
        result = await session.execute(select(User).where(User.chat_id == chat_id))
        user = result.scalars().first()
        if user:
            logger.debug(f"db_get_lang: found {chat_id} -> {user.language}")
            return user.language or "en"
        logger.debug(f"db_get_lang: not found in DB {chat_id}")
        return None
    except Exception as e:
        logger.exception("DB read error for %s: %s", chat_id, e)
        return None


async def redis_get_lang(redis, chat_id: int) -> Optional[str]:
    try:
        val = await redis.get(f"user:{chat_id}:lang")
        if not val:
            return None
        if isinstance(val, bytes):
            return val.decode()
        return val
    except Exception as e:
        logger.warning("Redis read error for %s: %s", chat_id, e)
        return None


async def get_lang_cache_then_db(session, redis, chat_id: int) -> Optional[str]:
    # 1) Try redis
    lang = await redis_get_lang(redis, chat_id)
    if lang:
        logger.debug("get_lang_cache_then_db: redis hit %s -> %s", chat_id, lang)
        return lang
    # 2) Fallback to DB
    lang = await db_get_lang(session, chat_id)
    if lang:
        try:
            await redis.set(f"user:{chat_id}:lang", lang, ex=CACHE_TTL)
        except Exception as e:
            logger.warning("Redis set failed for %s: %s", chat_id, e)
    return lang


async def ensure_user_exists(session, chat_id: int, username: Optional[str], first_name: Optional[str],
                             is_premium: Optional[bool], default_lang: str = "en",
                             added_by: Optional[str] = None) -> int:
    """
    Upsert minimal user with default_lang.
    Returns user id (int).
    Caller controls commit (so we don't commit here).
    """
    try:
        stmt = insert(User).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=default_lang,
            added_by=added_by,
        ).on_conflict_do_update(
            index_elements=[User.chat_id],
            set_={
                "username": username,
                "first_name": first_name,
                "is_premium": is_premium
            }
        ).returning(User.id)
        res = await session.execute(stmt)
        user_id = res.scalar_one()
        logger.info("ensure_user_exists: chat_id=%s id=%s", chat_id, user_id)
        return user_id
    except Exception as e:
        logger.exception("ensure_user_exists failed for %s: %s", chat_id, e)
        raise


async def upsert_user(session, chat_id: int, username: Optional[str], first_name: Optional[str],
                      is_premium: Optional[bool], language: str, added_by: Optional[str] = None) -> int:
    """
    Upsert full user record with language (used on lang selection).
    """
    try:
        stmt = insert(User).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=language,
            added_by=added_by,
        ).on_conflict_do_update(
            index_elements=[User.chat_id],
            set_={
                "username": username,
                "first_name": first_name,
                "is_premium": is_premium,
                "language": language,
                "added_by": added_by
            }
        ).returning(User.id)
        res = await session.execute(stmt)
        user_id = res.scalar_one()
        logger.info("upsert_user: chat_id=%s id=%s lang=%s", chat_id, user_id, language)
        return user_id
    except Exception as e:
        logger.exception("upsert_user failed for %s: %s", chat_id, e)
        raise
