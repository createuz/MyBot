# app/web/tg_updates.py
import time
from typing import Any, Dict

# aiogram imports
from aiogram.types import Update
from aiohttp import web

from app.core.config import conf
from app.core.logger import get_logger
from app.web.metrics import WEBHOOK_UPDATES, REQUESTS, REQUEST_LATENCY


# NOTE: use Dispatcher.feed_update for aiogram 3.22.0

def tg_updates_app() -> web.Application:
    """
    Returns an aiohttp sub-application that handles Telegram webhook POSTs.
    Mount this subapp at e.g. "/tg/webhooks/" so Telegram posts to https://.../tg/webhooks/
    """
    app = web.Application()
    app.router.add_post("", handle_update)  # POST to subapp root
    app.router.add_get("/health", lambda r: web.json_response({"status": "ok"}))
    return app


async def handle_update(request: web.Request) -> web.Response:
    """
    Handle incoming Telegram webhook update for aiogram 3.22.0.

    Steps:
      1. Validate secret token header if configured.
      2. Parse JSON payload.
      3. Build aiogram.types.Update using Update.model_validate(payload, context={"bot": bot})
      4. Call dispatcher.feed_update(update) (await it).
      5. Return 200 OK to Telegram.
    """
    # get request-scoped logger and request id if available
    req_logger = request.get("logger") or get_logger()
    rid = request.get("request_id")
    if rid:
        req_logger = req_logger.bind(rid=rid)

    start = time.time()
    REQUESTS.labels(method="POST", endpoint="/tg/webhooks/").inc()

    # 1) Secret token check (recommended)
    if getattr(conf, "webhook", None) and getattr(conf.webhook, "secret_token", None):
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_token != conf.webhook.secret_token:
            req_logger.warning("tg_updates: invalid secret token")
            return web.Response(status=401, text="Unauthorized")

    # 2) Parse JSON
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        req_logger.exception("tg_updates: invalid JSON payload: %s", e)
        return web.Response(status=400, text="Bad Request: invalid JSON")

    # 3) Convert to aiogram Update model (this binds bot via context if needed)
    bot = request.app.get("bot")  # bot was injected into app at setup_aiohttp_app time
    if bot is None:
        req_logger.error("tg_updates: bot instance not found on app")
        return web.Response(status=500, text="Bot not available")

    try:
        # Use model_validate to ensure proper types and context (aiogram 3.22.0 recommended)
        update = Update.model_validate(payload, context={"bot": bot})
    except Exception as e:
        req_logger.exception("tg_updates: failed to parse Update model: %s", e)
        # return 400 so Telegram won't retry with same bad payload forever
        return web.Response(status=400, text="Bad Request: invalid Update format")

    # 4) Dispatch to aiogram Dispatcher
    dp = request.app.get("dp")
    if dp is None:
        req_logger.error("tg_updates: dispatcher not found in app")
        return web.Response(status=500, text="Dispatcher not available")

    # increment webhook metric
    try:
        WEBHOOK_UPDATES.inc()
    except Exception:
        pass

    try:
        # aiogram 3.22.0: use feed_update(update)
        # This will run middlewares and handlers in dispatcher
        await dp.feed_update(update)
    except Exception as exc:
        # log and return 500 to let you know something went wrong server-side
        req_logger.exception("tg_updates: dispatcher.feed_update raised: %s", exc)
        # Returning 200 here could silence Telegram retries; choose 200 if you prefer to ack.
        return web.Response(status=500, text="Internal Server Error")

    # Observe latency
    latency = time.time() - start
    try:
        REQUEST_LATENCY.labels(endpoint="/tg/webhooks/").observe(latency)
    except Exception:
        pass

    return web.Response(status=200, text="OK")
