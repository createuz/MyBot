# app/utils/user_service.py
from sqlalchemy.dialects.postgresql import insert
from app.db.models import User
from app.core.logger import get_logger

logger = get_logger()
CACHE_TTL = 7 * 24 * 3600  # 7 days

# Redis-only get
async def redis_get_lang(redis, chat_id: int) -> str | None:
    if not redis:
        return None
    key = f"user:{chat_id}:lang"
    try:
        lang = await redis.get(key)
        if lang:
            logger.debug(f"redis_get_lang hit {chat_id} -> {lang}")
            return lang
        logger.debug(f"redis_get_lang miss {chat_id}")
        return None
    except Exception as e:
        logger.warning(f"Redis GET error for {chat_id}: {e}")
        return None

# DB-only get
async def db_get_lang(session, chat_id: int) -> str | None:
    try:
        row = await session.execute(User.__table__.select().where(User.chat_id == chat_id))
        user = row.scalar_one_or_none()
        if user:
            logger.debug(f"db_get_lang found {chat_id} -> {user.language}")
            return user.language or "en"
        return None
    except Exception as e:
        logger.exception(f"DB read error for {chat_id}: {e}")
        return None

# Combined: redis -> db (and cache db result)
async def get_lang_cache_then_db(session, redis, chat_id: int) -> str | None:
    lang = await redis_get_lang(redis, chat_id)
    if lang:
        return lang
    lang = await db_get_lang(session, chat_id)
    if lang and redis:
        try:
            await redis.set(f"user:{chat_id}:lang", lang, ex=CACHE_TTL)
            logger.debug(f"Cached lang for {chat_id} -> {lang}")
        except Exception as e:
            logger.warning(f"Redis SET failed for {chat_id}: {e}")
    return lang

# Ensure user exists (create if not)
async def ensure_user_exists(session, chat_id: int, username: str | None, first_name: str | None,
                             is_premium: bool | None, default_lang: str = "en") -> int:
    try:
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
                "is_premium": is_premium
                # intentionally not overwriting language here
            }
        ).returning(User.id)
        res = await session.execute(stmt)
        user_id = res.scalar_one()
        logger.info(f"ensure_user_exists: chat_id={chat_id}, id={user_id}")
        return user_id
    except Exception as e:
        logger.exception(f"ensure_user_exists failed for {chat_id}: {e}")
        raise

# Upsert user including language (used when user selects language)
async def upsert_user(session, chat_id: int, username: str | None, first_name: str | None,
                      is_premium: bool | None, language: str, added_by: str | None = None) -> int:
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
        logger.debug(f"upsert_user: chat_id={chat_id}, lang={language} -> id={user_id}")
        return user_id
    except Exception as e:
        logger.exception(f"upsert_user failed for {chat_id}: {e}")
        raise
