# app/bot/middlewares/db_middleware.py
from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable
from app.core.logger import get_logger
from app.db.lazy_session import LazySessionProxy
from app.db.session import db

class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        request_id = data.get("request_id")
        logger = get_logger(request_id)

        # Provide lazy proxy
        proxy = LazySessionProxy(db._SessionMaker)
        data["db"] = proxy

        try:
            result = await handler(event, data)

            # If no real session was created — nothing to commit/close
            if not proxy.session_created:
                logger.debug("No DB session created during request — skipping commit/close")
                return result

            session = proxy._session

            # If handler committed itself - skip middleware commit
            if getattr(session, "info", {}).get("committed_by_handler"):
                logger.debug("Handler committed; skipping middleware commit")
                try:
                    await session.close()
                except Exception as e:
                    logger.warning(f"Close session failed: {e}")
                return result

            # Commit only if session has pending changes
            try:
                has_changes = bool(session.new) or bool(session.dirty) or bool(session.deleted)
            except Exception:
                has_changes = True

            if has_changes:
                try:
                    await session.commit()
                    logger.info("DB committed (middleware)")
                except Exception as e:
                    try:
                        await session.rollback()
                    except Exception as re:
                        logger.error(f"Rollback failed: {re}")
                    logger.exception(f"DB commit failed in middleware: {e}")
                    raise
            else:
                logger.debug("No DB changes detected — skipping commit (middleware)")

            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Close session failed: {e}")

            return result

        except Exception as exc:
            # Exception handling: rollback if session created and not handler-committed
            if proxy.session_created:
                session = proxy._session
                if getattr(session, "info", {}).get("committed_by_handler"):
                    logger.warning("Handler raised after committing — skipping rollback")
                else:
                    try:
                        await session.rollback()
                        logger.info("DB rolled back (middleware)")
                    except Exception as rbe:
                        logger.error(f"Rollback failed: {rbe}")
                try:
                    await session.close()
                except Exception as e:
                    logger.warning(f"Close session failed after exception: {e}")
            else:
                logger.debug("Exception occurred but DB session was never created")
            logger.exception("Exception in handler (caught in middleware)")
            raise
