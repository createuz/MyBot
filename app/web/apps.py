# app/web/app.py
import aiojobs
from aiohttp import web

from app.core.logger import get_logger
# DB / Redis helpers
from app.db.session import init_db, dispose_db
from app.utils.redis_client import RedisManager
from app.web.health import register as register_health
from app.web.metrics import register as register_metrics
from app.web.middlewares import request_id_middleware
from app.web.tg_updates import tg_updates_app

DEFAULT_SUBAPPS = (
    ("/tg/webhooks/", tg_updates_app),
)
redis_manager = RedisManager()

async def aiohttp_on_startup(app: web.Application) -> None:
    logger = get_logger()
    dp = app["dp"]
    bot = app.get("bot")
    logger.info("aiohttp_on_startup: init redis & db")
    await redis_manager.init()
    await init_db()
    workflow_data = {"app": app, "dispatcher": dp}
    if bot is not None:
        workflow_data["bot"] = bot
    await dp.emit_startup(**workflow_data)
    logger.info("aiohttp_on_startup: dispatcher started")


async def aiohttp_on_shutdown(app: web.Application) -> None:
    logger = get_logger()
    dp = app["dp"]
    bot = app.get("bot")
    logger.info("aiohttp_on_shutdown: shutting down dispatcher + resources")

    # emit dispatcher shutdown
    workflow_data = {"app": app, "dispatcher": dp}
    if bot is not None:
        workflow_data["bot"] = bot
    await dp.emit_shutdown(**workflow_data)

    # close scheduler if present
    scheduler = app.get("scheduler")
    if scheduler is not None:
        try:
            await scheduler.close()
        except Exception:
            logger.warning("scheduler close threw")

    # close dispatcher storage
    try:
        await dp.storage.close()
    except Exception:
        logger.debug("dispatcher.storage close ignored")

    # close bot session
    if bot is not None:
        try:
            await bot.session.close()
        except Exception:
            logger.debug("bot.session close ignored")

    # close redis and dispose db
    try:
        await redis_manager.close()
    except Exception:
        logger.warning("close_redis failed")
    try:
        await dispose_db()
    except Exception:
        logger.warning("dispose_db failed")

    logger.info("aiohttp_on_shutdown: done")


async def setup_aiohttp_app(bot, dp) -> web.Application:
    """
    Create main aiohttp app, mount subapps, register health/metrics and lifecycle hooks.
    """
    logger = get_logger()
    scheduler = aiojobs.Scheduler()
    app = web.Application(middlewares=[request_id_middleware])

    # add subapps
    for prefix, factory in DEFAULT_SUBAPPS:
        subapp = factory()
        subapp["bot"] = bot
        subapp["dp"] = dp
        subapp["scheduler"] = scheduler
        app.add_subapp(prefix, subapp)

    # global context
    app["bot"] = bot
    app["dp"] = dp
    app["scheduler"] = scheduler

    # register endpoints
    register_health(app)
    register_metrics(app)

    # lifecycle hooks
    app.on_startup.append(aiohttp_on_startup)
    app.on_shutdown.append(aiohttp_on_shutdown)

    logger.info("setup_aiohttp_app: ready")
    return app
