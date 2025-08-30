# app/web/tg_updates.py
import time
from typing import Any, Dict

from aiogram.types import Update
from aiohttp import web

from app.core.config import conf
from app.core.logger import get_logger
from app.web.metrics import WEBHOOK_UPDATES, REQUESTS, REQUEST_LATENCY


def tg_updates_app() -> web.Application:
    app = web.Application()
    app.router.add_post("", handle_update)
    app.router.add_get("/health", lambda r: web.json_response({"status": "ok"}))
    return app


async def handle_update(request: web.Request) -> web.Response:
    req_logger = request.get("logger") or get_logger()
    rid = request.get("request_id")
    if rid:
        req_logger = req_logger.bind(rid=rid)

    start = time.time()
    REQUESTS.labels(method="POST", endpoint="/tg/webhooks/").inc()

    # secret token check
    if getattr(conf, "webhook_secret", None):
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_token != conf.webhook.secret:
            req_logger.warning("tg_updates: invalid secret token")
            return web.Response(status=401, text="Unauthorized")

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        req_logger.exception("tg_updates: invalid json")
        return web.Response(status=400, text="Bad Request")

    bot = request.app.get("bot")
    if bot is None:
        req_logger.error("tg_updates: bot not found")
        return web.Response(status=500, text="Server error")

    # Build aiogram Update model (validates)
    try:
        update = Update.model_validate(payload, context={"bot": bot})
    except Exception as e:
        req_logger.exception("tg_updates: invalid Update model")
        return web.Response(status=400, text="Bad Request")

    dp = request.app.get("dp")
    if dp is None:
        req_logger.error("tg_updates: dispatcher not found")
        return web.Response(status=500, text="Server error")

    try:
        WEBHOOK_UPDATES.inc()
    except Exception:
        pass

    try:
        await dp.feed_update(update)
    except Exception as exc:
        req_logger.exception("tg_updates: dispatcher.feed_update failed")
        # Returning 500 to surface server errors so you can see and fix them; change to 200 if you prefer ack
        return web.Response(status=500, text="Internal Server Error")

    latency = time.time() - start
    try:
        REQUEST_LATENCY.labels(endpoint="/tg/webhooks/").observe(latency)
    except Exception:
        pass

    return web.Response(status=200, text="OK")
