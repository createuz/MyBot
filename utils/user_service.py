# app/utils/user_service.py
from sqlalchemy.dialects.postgresql import insert

from core.logger import get_logger
from db.models import User

logger = get_logger()
CACHE_TTL = 7 * 24 * 3600  # 7 days


async def get_user_language(session, redis, chat_id: int) -> str:
    key = f"user:{chat_id}:lang"
    # 1) try redis
    if redis:
        try:
            lang = await redis.get(key)
            if lang:
                return lang
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
    # 2) fallback to DB
    row = await session.execute(
        User.__table__.select().where(User.chat_id == chat_id)
    )
    user = row.scalar_one_or_none()
    if user:
        # best-effort cache set
        try:
            if redis:
                await redis.set(key, user.language, ex=CACHE_TTL)
        except Exception as e:
            logger.error(f"Redis SET after DB read failed: {e}")
        return user.language
    # default
    return "en"


async def upsert_user(session, chat_id: int, username: str | None, first_name: str | None,
                      is_premium: bool | None, language: str, added_by: str | None):
    """
    Atomically insert or update user row and return user's id.
    Uses Postgres ON CONFLICT.
    """
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
            "username": getattr(stmt := insert(User), "excluded").username if False else insert(User).excluded.username
        }
    )
    # The above is a bit clumsy with `excluded` mapping in SQLAlchemy; easier: build set_ manually
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
    row = res.scalar_one()
    return row  # returns id
