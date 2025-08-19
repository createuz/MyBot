# app/web/middlewares.py
import uuid
from aiohttp import web
from app.core.logger import get_logger


@web.middleware
async def request_id_middleware(request: web.Request, handler):
    rid = uuid.uuid4().hex
    # bind logger per-request if you use structlog
    logger = get_logger(rid)
    request["request_id"] = rid
    request["logger"] = logger
    try:
        response = await handler(request)
        # attach request id header for correlation
        response.headers["X-Request-Id"] = rid
        return response
    except web.HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in web handler: %s", e)
        raise
