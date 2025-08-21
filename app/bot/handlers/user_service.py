# app/utils/user_service.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from app.core.logger import get_logger

from app.db.models import User

logger = get_logger()
CACHE_TTL = 7 * 24 * 3600  # 7 days

async def get_lang_cache_then_db(session, redis_client, chat_id: int) -> Optional[str]:
    """
    Redis-first: if redis has confirmed language -> return it.
    Otherwise query DB: if DB.language is not None -> set redis and return it.
    If DB.language is None or user not found -> return None (means ask language).
    """
    # 1) redis
    try:
        if redis_client:
            val = await redis_client.get(f"user:{chat_id}:lang")
            if val:
                if isinstance(val, bytes):
                    lang = val.decode()
                else:
                    lang = str(val)
                logger.debug("get_lang: redis hit %s -> %s", chat_id, lang)
                return lang
    except Exception as e:
        logger.warning("get_lang: redis read failed %s: %s", chat_id, e)
        # continue to DB

    # 2) DB
    try:
        result = await session.execute(select(User).where(User.chat_id == chat_id))
        user = result.scalars().first()
        if not user:
            logger.debug("get_lang: user not in DB %s", chat_id)
            return None
        if user.language:
            # best-effort set redis
            try:
                if redis_client:
                    await redis_client.set(f"user:{chat_id}:lang", user.language, ex=CACHE_TTL)
            except Exception:
                logger.warning("get_lang: redis set failed")
            return user.language
        # language is None in DB -> ask the user
        logger.debug("get_lang: user exists but language NULL %s", chat_id)
        return None
    except Exception as e:
        logger.exception("get_lang: DB read error %s: %s", chat_id, e)
        return None


async def ensure_user_insert_if_missing(session, chat_id: int, username: Optional[str], first_name: Optional[str],
                                        is_premium: Optional[bool], added_by: Optional[str] = None) -> Optional[int]:
    """
    Insert user if not exists; language stays NULL until user chooses.
    Returns user.id or None on error.
    """
    try:
        ins = pg_insert(User).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=None,
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
        uid = res.scalar_one()
        logger.info("ensure_user: chat_id=%s id=%s", chat_id, uid)
        return uid
    except SQLAlchemyError as e:
        logger.exception("ensure_user DB error %s: %s", chat_id, e)
        return None
    except Exception as e:
        logger.exception("ensure_user unexpected %s: %s", chat_id, e)
        return None


async def update_user_language(session, chat_id: int, language: str) -> Optional[int]:
    """
    Upsert language field (set to chosen language).
    Returns user.id or None on error.
    """
    try:
        ins = pg_insert(User).values(
            chat_id=chat_id,
            language=language,
        )
        stmt = ins.on_conflict_do_update(
            index_elements=[User.chat_id],
            set_={"language": ins.excluded.language}
        ).returning(User.id)
        res = await session.execute(stmt)
        uid = res.scalar_one()
        logger.info("update_user_language: chat_id=%s id=%s lang=%s", chat_id, uid, language)
        return uid
    except Exception as e:
        logger.exception("update_user_language failed %s: %s", chat_id, e)
        return None
