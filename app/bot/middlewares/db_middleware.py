# app/bot/middlewares/db_middleware.py
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware

from app.core.logger import get_logger
from app.db.lazy_session import LazySessionProxy
from app.db.session import AsyncSessionLocal  # async_sessionmaker instance or callable


class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        request_id = data.get("request_id")
        logger = get_logger(request_id)
        proxy = LazySessionProxy(session_maker=AsyncSessionLocal)
        data["db"] = proxy

        try:
            result = await handler(event, data)
        except Exception as exc:
            # handler raised — rollback if session exists, close session
            if proxy.session_created:
                sess = proxy.get_underlying_session()
                try:
                    if not sess.info.get("committed_by_handler"):
                        await sess.rollback()
                        logger.info("DBSessionMiddleware: rollback due to handler exception")
                except Exception:
                    logger.exception("DBSessionMiddleware: rollback failed")
                try:
                    await sess.close()
                except Exception:
                    logger.exception("DBSessionMiddleware: session close failed")
            logger.exception("Exception in handler")
            raise

        # handler returned successfully
        if not proxy.session_created:
            logger.debug("DBSessionMiddleware: no DB session used by handler")
            return result

        sess = proxy.get_underlying_session()
        # if handler already committed explicitly, skip commit
        if sess.info.get("committed_by_handler"):
            try:
                await sess.close()
            except Exception:
                logger.exception("DBSessionMiddleware: session close failed after handler commit")
            logger.debug("DBSessionMiddleware: handler committed, middleware skip")
            return result

        # commit only if there are changes or active transaction
        try:
            has_changes = bool(sess.new) or bool(sess.dirty) or bool(sess.deleted) or bool(sess.in_transaction())
        except Exception:
            has_changes = True

        if has_changes:
            try:
                await sess.commit()
                logger.info("DBSessionMiddleware: committed")
            except Exception:
                try:
                    await sess.rollback()
                except Exception:
                    logger.exception("DBSessionMiddleware: rollback failed after commit failure")
                logger.exception("DBSessionMiddleware: commit failed")
                raise
        else:
            logger.debug("DBSessionMiddleware: nothing to commit")

        try:
            await sess.close()
        except Exception:
            logger.exception("DBSessionMiddleware: session close failed after commit")
        return result
