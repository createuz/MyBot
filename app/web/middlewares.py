# app/web/middlewares.py
import uuid

from aiohttp import web

from app.core.logger import get_logger


@web.middleware
async def request_id_middleware(request: web.Request, handler):
    rid = uuid.uuid4().hex
    logger = get_logger(rid)
    request["request_id"] = rid
    request["logger"] = logger
    try:
        response = await handler(request)
        response.headers["X-Request-Id"] = rid
        return response
    except Exception as e:
        logger.exception("Unhandled web exception")
        raise
