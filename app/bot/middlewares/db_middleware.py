# app/bot/middlewares/db_middleware.py
from aiogram import BaseMiddleware

from app.core.logger import get_logger
from app.db.lazy_session import LazySessionProxy
from app.db.session import AsyncSessionLocal


class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        request_id = data.get("request_id")
        logger = get_logger(request_id)
        proxy = LazySessionProxy(session_maker=AsyncSessionLocal)
        data["db"] = proxy
        try:
            result = await handler(event, data)
            # if session never created, skip commit/close
            if not proxy.session_created:
                logger.debug("DBSessionMiddleware: no session created")
                return result
            session = proxy.get_underlying_session()
            if session.info.get("committed_by_handler"):
                logger.debug("DBSessionMiddleware: handler already committed")
                await session.close()
                return result
            # commit only if changes or in_transaction
            try:
                has_changes = bool(session.new) or bool(session.dirty) or bool(session.deleted) or bool(
                    session.in_transaction())
            except Exception:
                has_changes = True
            if has_changes:
                await session.commit()
                logger.info("DBSessionMiddleware: committed")
            else:
                logger.debug("DBSessionMiddleware: nothing to commit")
            await session.close()
            return result
        except Exception as exc:
            if proxy.session_created:
                session = proxy.get_underlying_session()
                if not session.info.get("committed_by_handler"):
                    try:
                        await session.rollback()
                        logger.info("DBSessionMiddleware: rolled back due to exception")
                    except Exception:
                        logger.exception("rollback failed")
                try:
                    await session.close()
                except Exception:
                    logger.exception("session close failed")
            logger.exception("Exception in handler")
            raise
