# app/utils/user_service.py

from sqlalchemy.dialects.postgresql import insert

from core.logger import get_logger
from db import User

logger = get_logger()
CACHE_TTL = 7 * 24 * 3600  # 7 days


# --- Redis-only: get language by chat id (no DB)
async def redis_get_lang(redis, chat_id: int) -> str | None:
    if not redis:
        return None
    key = f"user:{chat_id}:lang"
    try:
        lang = await redis.get(key)
        if lang:
            logger.debug(f"redis_get_lang: hit for {chat_id} -> {lang}")
            return lang
        logger.debug(f"redis_get_lang: miss for {chat_id}")
        return None
    except Exception as e:
        logger.warning(f"Redis GET error for {chat_id}: {e}")
        return None


# --- DB-only: get language (no Redis actions)
async def db_get_lang(session, chat_id: int) -> str | None:
    try:
        row = await session.execute(User.__table__.select().where(User.chat_id == chat_id))
        user = row.scalar_one_or_none()
        if user:
            logger.debug(f"db_get_lang: found in DB {chat_id} -> {user.language}")
            return user.language or "en"
        logger.debug(f"db_get_lang: not found in DB {chat_id}")
        return None
    except Exception as e:
        logger.exception(f"DB read error for {chat_id}: {e}")
        return None


# --- Combined helper (calls redis first, then DB; returns language or None)
async def get_lang_cache_then_db(session, redis, chat_id: int) -> str | None:
    # 1) try redis
    lang = await redis_get_lang(redis, chat_id)
    if lang:
        return lang
    # 2) fallback DB (uses session)
    lang = await db_get_lang(session, chat_id)
    if lang and redis:
        # best-effort cache set
        try:
            await redis.set(f"user:{chat_id}:lang", lang, ex=CACHE_TTL)
            logger.debug(f"Cached lang in Redis for {chat_id}: {lang}")
        except Exception as e:
            logger.warning(f"Redis SET failed for {chat_id}: {e}")
    return lang


# --- Ensure user exists: create user if not exists (atomically)
async def ensure_user_exists(session, chat_id: int, username: str | None, first_name: str | None,
                             is_premium: bool | None, default_lang: str = "en") -> int:
    """
    Inserts the user with default_lang if not exists;
    If exists, this operation doesn't overwrite language (keep existing) to avoid undesired overrides.
    Returns user.id.
    """
    try:
        # We'll perform ON CONFLICT DO UPDATE but avoid changing language if exists:
        stmt = insert(User).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=default_lang
        ).on_conflict_do_update(
            index_elements=["chat_id"],
            set_={
                "username": username,
                "first_name": first_name,
                "is_premium": is_premium,
                # don't overwrite language if already set
            }
        ).returning(User.id)
        res = await session.execute(stmt)
        user_id = res.scalar_one()
        logger.info(f"ensure_user_exists: chat_id={chat_id}, id={user_id}")
        return user_id
    except Exception as e:
        logger.exception(f"ensure_user_exists failed for {chat_id}: {e}")
        raise


# --- Upsert user language (atomic) — used when user chooses language
async def upsert_user(session, chat_id: int, username: str | None, first_name: str | None,
                      is_premium: bool | None, language: str, added_by: str | None = None) -> int:
    """
    Atomically insert or update language (and other fields). Returns user.id
    """
    try:
        stmt = insert(User).values(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language=language,
            added_by=added_by
        ).on_conflict_do_update(
            index_elements=["chat_id"],
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
        logger.debug(f"upsert_user: chat_id={chat_id} language={language} -> id={user_id}")
        return user_id
    except Exception as e:
        logger.exception(f"upsert_user failed for {chat_id}: {e}")
        raise
