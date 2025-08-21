# app/utils/db_helpers.py
from typing import Any

from app.core.logger import get_logger

logger = get_logger()


async def session_has_changes(session: Any) -> bool:
    """
    Return True if session.new/dirty/deleted present or in transaction.
    Works with LazySessionProxy or AsyncSession.
    """
    try:
        return bool(session.new) or bool(session.dirty) or bool(session.deleted) or bool(session.in_transaction())
    except Exception:
        # If cannot introspect, be conservative and assume changed
        return True


async def safe_commit_if_needed(session: Any) -> None:
    if not session:
        return
    if not getattr(session, "session_created", True) and not getattr(session, "_session", None):
        # no underlying session created
        return
    try:
        if await session_has_changes(session):
            await session.commit()
            logger.info("DB: committed by handler/helper")
    except Exception:
        try:
            await session.rollback()
            logger.exception("DB: rollback after commit failure")
        except Exception:
            logger.exception("DB: rollback failed")
