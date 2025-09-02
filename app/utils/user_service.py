# app/utils/user_service.py
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.logger import get_logger
from app.db.models import User

logger = get_logger()
CACHE_TTL = 7 * 24 * 3600


async def redis_get_lang(redis_client, chat_id: int) -> Optional[str]:
    if redis_client is None:
        return None
    try:
        key = f"user:{chat_id}:lang"
        val = await redis_client.get(key)
        if val is None:
            return None
        if isinstance(val, bytes):
            return val.decode("utf-8", errors="ignore")
        return str(val)
    except Exception as e:
        logger.warning("redis_get_lang error %s: %s", chat_id, e)
        return None


async def db_get_lang(session, chat_id: int) -> Optional[str]:
    try:
        res = await session.execute(select(User).where(User.chat_id == chat_id))
        user = res.scalars().first()
        if not user:
            return None
        return user.language
    except Exception as e:
        logger.exception("DB read error for %s: %s", chat_id, e)
        return None


async def get_lang_cache_then_db(session, redis_client, chat_id: int) -> Optional[str]:
    lang = await redis_get_lang(redis_client, chat_id)
    if lang:
        logger.debug("redis hit %s -> %s", chat_id, lang)
        return lang
    lang = await db_get_lang(session, chat_id)
    if lang:
        try:
            if redis_client is not None:
                await redis_client.set(f"user:{chat_id}:lang", lang, ex=CACHE_TTL)
        except Exception:
            logger.warning("redis set failed for %s", chat_id)
    return lang


async def ensure_user_exists(session, chat_id: int, username: Optional[str], first_name: Optional[str],
                             is_premium: Optional[bool], default_lang: Optional[str] = None,
                             added_by: Optional[str] = None) -> int:
    try:
        ins = pg_insert(User).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=default_lang,
            added_by=added_by
        )
        stmt = ins.on_conflict_do_update(
            index_elements=[User.chat_id],
            set_={
                "username": ins.excluded.username,
                "first_name": ins.excluded.first_name,
                "is_premium": ins.excluded.is_premium,
            }
        ).returning(User.id)
        res = await session.execute(stmt)
        user_id = res.scalar_one()
        logger.info("ensure_user_exists: chat_id=%s id=%s", chat_id, user_id)
        return user_id
    except SQLAlchemyError as e:
        logger.exception("ensure_user_exists failed for %s: %s", chat_id, e)
        raise


async def upsert_user_language(session, chat_id: int, language: str) -> int:
    try:
        ins = pg_insert(User).values(chat_id=chat_id, language=language)
        stmt = ins.on_conflict_do_update(
            index_elements=[User.chat_id],
            set_={"language": ins.excluded.language}
        ).returning(User.id)
        res = await session.execute(stmt)
        user_id = res.scalar_one()
        logger.info("upsert_user_language: chat_id=%s id=%s lang=%s", chat_id, user_id, language)
        return user_id
    except Exception as e:
        logger.exception("upsert_user_language failed for %s: %s", chat_id, e)
        raise
