# app/utils/db_helpers.py
from typing import Any

from app.core.logger import get_logger

logger = get_logger()


async def session_has_changes(session: Any) -> bool:
    try:
        return bool(session.new) or bool(session.dirty) or bool(session.deleted) or bool(session.in_transaction())
    except Exception:
        return True


async def safe_commit_if_needed(session: Any) -> None:
    if not session:
        return
    # if using LazySessionProxy, get underlying session for introspection
    real = getattr(session, "get_underlying_session", None)
    if real:
        sess = session.get_underlying_session()
    else:
        sess = session
    if not sess:
        return
    try:
        if await session_has_changes(sess):
            await sess.commit()
            logger.info("DB commit (safe_commit_if_needed)")
    except Exception:
        try:
            await sess.rollback()
            logger.exception("DB rollback after commit error")
        except Exception:
            logger.exception("DB rollback failed")
