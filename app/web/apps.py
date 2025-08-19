# app/web/app.py
from typing import Tuple

import aiojobs
from aiohttp import web

from app.core.logger import get_logger
from app.web.health import register as register_health
from app.web.metrics import register as register_metrics
from app.web.tg_updates import tg_updates_app

# If you have other subapps, add them here as (prefix, subapp_callable)
DEFAULT_SUBAPPS: Tuple[tuple[str, web.Application], ...] = (
    ("/tg/webhooks/", tg_updates_app),
)


async def aiohttp_on_startup(app: web.Application) -> None:
    dp = app["dp"]
    logger = get_logger()
    logger.info("aiohttp_on_startup: emitting dispatcher startup")
    workflow_data = {"app": app, "dispatcher": dp}
    if "bot" in app:
        workflow_data["bot"] = app["bot"]
    await dp.emit_startup(**workflow_data)


async def aiohttp_on_shutdown(app: web.Application) -> None:
    dp = app["dp"]
    logger = get_logger()
    logger.info("aiohttp_on_shutdown: emitting dispatcher shutdown")
    # Properly close scheduler if present
    scheduler = app.get("scheduler")
    if scheduler is not None:
        try:
            # aiojobs Scheduler has close() async in newer versions
            await scheduler.close()
        except AttributeError:
            try:
                scheduler.close()
            except Exception as e:
                logger.warning("Scheduler close fallback failed: %s", e)
        except Exception as e:
            logger.warning("Scheduler close failed: %s", e)

    workflow_data = {"app": app, "dispatcher": dp}
    if "bot" in app:
        workflow_data["bot"] = app["bot"]
    await dp.emit_shutdown(**workflow_data)

    # close bot.session, storage, pools if still present
    try:
        if "bot" in app:
            bot = app["bot"]
            try:
                await bot.session.close()
            except Exception:
                logger.debug("bot.session close ignored")
        if "dp" in app:
            dispatcher = app["dp"]
            try:
                await dispatcher.storage.close()
            except Exception:
                logger.debug("dispatcher.storage close ignored")
    except Exception as e:
        logger.exception("Error during aiohttp shutdown cleanup: %s", e)


async def setup_aiohttp_app(bot, dp) -> web.Application:
    """
    Create aiohttp main app, mount subapps (webhooks), and register startup/shutdown hooks.
    :param bot: aiogram.Bot instance (optional)
    :param dp: aiogram.Dispatcher instance (required)
    :return: aiohttp.web.Application
    """
    logger = get_logger()
    scheduler = aiojobs.Scheduler()
    app = web.Application()
    # mount subapps
    for prefix, subapp_factory in DEFAULT_SUBAPPS:
        subapp = subapp_factory()  # subapp_factory returns an aiohttp Application
        # inject dp, bot, scheduler into subapp
        subapp["bot"] = bot
        subapp["dp"] = dp
        subapp["scheduler"] = scheduler
        app.add_subapp(prefix, subapp)

    # global resources
    app["bot"] = bot
    app["dp"] = dp
    app["scheduler"] = scheduler

    # register health and metrics
    register_health(app)
    register_metrics(app)

    # lifecycle hooks
    app.on_startup.append(aiohttp_on_startup)
    app.on_shutdown.append(aiohttp_on_shutdown)

    logger.info("setup_aiohttp_app: app configured with %s subapps", len(DEFAULT_SUBAPPS))
    return app
