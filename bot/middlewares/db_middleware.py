# app/bot/middlewares/db_middleware.py
from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable
from db.session import db
from core.logger import get_logger

class DBSessionMiddleware(BaseMiddleware):
    """
    Per-update session provider.
    Commit is executed only if the session has pending changes (new/dirty/deleted),
    or if the handler explicitly committed and set session.info['committed_by_handler'] = True.
    """
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        request_id = data.get("request_id")
        logger = get_logger(request_id)

        async with db.get_session() as session:
            data["db"] = session
            try:
                result = await handler(event, data)

                # If handler committed itself, skip middleware commit
                if session.info.get("committed_by_handler"):
                    logger.debug("Handler already committed — skipping middleware commit")
                    return result

                # Commit only if there are pending changes (new/dirty/deleted)
                try:
                    has_changes = bool(session.new) or bool(session.dirty) or bool(session.deleted)
                except Exception:
                    # In unlikely failures reading session attrs, be safe and assume changes
                    has_changes = True

                if has_changes:
                    try:
                        await session.commit()
                        logger.info("DB committed (middleware)")
                    except Exception as e:
                        try:
                            await session.rollback()
                        except Exception as re:
                            logger.error(f"Rollback failed after commit error: {re}")
                        logger.exception(f"DB commit failed in middleware: {e}")
                        raise
                else:
                    logger.debug("No DB changes detected — skipping commit (middleware)")

                return result

            except Exception as exc:
                # If handler committed already, don't attempt rollback here (can't rollback committed transaction)
                if session.info.get("committed_by_handler"):
                    logger.warning("Handler raised after committing. Skipping rollback.")
                else:
                    try:
                        await session.rollback()
                        logger.info("DB rolled back (middleware) due to exception in handler")
                    except Exception as rbe:
                        logger.error(f"Rollback failed in middleware: {rbe}")
                logger.exception("Exception in handler (caught in middleware).")
                raise
