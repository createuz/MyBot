# app/utils/user_service.py
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.logger import get_logger
from app.db.models import User

logger = get_logger()
CACHE_TTL = 7 * 24 * 3600  # 7 kun (sekundlarda)


async def redis_get_lang(redis_client, chat_id: int) -> Optional[str]:
    try:
        if redis_client is None:
            return None
        key = f"user:{chat_id}:lang"
        val = await redis_client.get(key)
        if val is None:
            return None
        if isinstance(val, bytes):
            try:
                return val.decode()
            except Exception:
                return val.decode("utf-8", errors="ignore")
        return str(val)
    except Exception as e:
        logger.warning("redis_get_lang error for %s: %s", chat_id, e)
        return None


async def db_get_lang(session, chat_id: int) -> Optional[str]:
    try:
        result = await session.execute(select(User).where(User.chat_id == chat_id))
        user = result.scalars().first()
        if user:
            lang = user.language or "en"
            logger.debug("db_get_lang: found %s -> %s", chat_id, lang)
            return lang
        logger.debug("db_get_lang: not found in DB for %s", chat_id)
        return None
    except Exception as e:
        logger.exception("DB read error for %s: %s", chat_id, e)
        return None


async def get_lang_cache_then_db(session, redis_client, chat_id: int) -> Optional[str]:
    # 1) Try redis
    lang = await redis_get_lang(redis_client, chat_id)
    if lang:
        logger.debug("get_lang_cache_then_db: redis hit %s -> %s", chat_id, lang)
        return lang

    # 2) Redis miss -> DB
    lang = await db_get_lang(session, chat_id)
    if lang:
        try:
            if redis_client is not None:
                await redis_client.set(f"user:{chat_id}:lang", lang, ex=CACHE_TTL)
        except Exception as e:
            logger.warning("get_lang_cache_then_db: redis set failed for %s: %s", chat_id, e)
    return lang


async def ensure_user_exists(session, chat_id: int, username: Optional[str], first_name: Optional[str],
                             is_premium: Optional[bool], default_lang: str = "en",
                             added_by: Optional[str] = None) -> int:
    """
    Minimal upsert: user mavjud bo'lmasa qo'shadi, mavjud bo'lsa ba'zi maydonlarni yangilaydi.
    Caller (handler) commit/rollback ni boshqaradi (bu funksiya commit qilmaydi).
    Returns: user.id (int)
    """
    try:
        ins = pg_insert(User).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=default_lang,
            added_by=added_by,
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
    except Exception as e:
        logger.exception("ensure_user_exists unexpected error for %s: %s", chat_id, e)
        raise


async def upsert_user(session, chat_id: int, username: Optional[str], first_name: Optional[str],
                      is_premium: Optional[bool], language: str, added_by: Optional[str] = None) -> int:
    """
    To'liq upsert: language maydonini ham yangilaydi.
    Caller commit/rollback ni boshqaradi.
    """
    try:
        ins = pg_insert(User).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=language,
            added_by=added_by,
        )

        stmt = ins.on_conflict_do_update(
            index_elements=[User.chat_id],
            set_={
                "username": ins.excluded.username,
                "first_name": ins.excluded.first_name,
                "is_premium": ins.excluded.is_premium,
                "language": ins.excluded.language,
                "added_by": ins.excluded.added_by
            }
        ).returning(User.id)

        res = await session.execute(stmt)
        user_id = res.scalar_one()
        logger.info("upsert_user: chat_id=%s id=%s lang=%s", chat_id, user_id, language)
        return user_id
    except SQLAlchemyError as e:
        logger.exception("upsert_user failed for %s: %s", chat_id, e)
        raise
    except Exception as e:
        logger.exception("upsert_user unexpected error for %s: %s", chat_id, e)
        raise
