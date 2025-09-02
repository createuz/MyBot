# main.py
import asyncio
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import start as start_pkg, callbacks as cb_pkg, lang_cmd as lang_pkg
from app.bot.middlewares.db_middleware import DBSessionMiddleware
from app.bot.middlewares.request_id_middleware import RequestIDMiddleware
from app.core.config import conf
from app.core.logger import get_logger
from app.db.session import init_db, dispose_db
from app.utils.redis_manager import RedisManager

logger = get_logger()


async def create_bot_and_dp():
    bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.outer_middleware(RequestIDMiddleware())
    dp.update.outer_middleware(DBSessionMiddleware())
    dp.include_router(start_pkg.router)
    dp.include_router(cb_pkg.router)
    dp.include_router(lang_pkg.router)
    return bot, dp


async def startup(bot, dp):
    await RedisManager.init()
    await init_db()
    logger.info("startup finished")


# async def startup_sequence(bot: Bot, dp: Dispatcher) -> None:
#     logger.info("Startup: initializing Redis")
#     await RedisManager.init()
#     logger.info("Startup: initializing DB (create tables if needed)")
#     await init_db()
#     logger.info("Startup finished")


# async def shutdown_sequence(bot: Bot, dp: Dispatcher) -> None:
#     logger.info("Shutdown: closing dispatcher storage")
#     try:
#         await dp.storage.close()
#     except Exception:
#         logger.exception("Error closing dispatcher storage")
#
#     logger.info("Shutdown: closing bot session")
#     try:
#         await bot.session.close()
#     except Exception:
#         logger.exception("Error closing bot.session")
#
#     logger.info("Shutdown: closing Redis")
#     try:
#         await RedisManager.close()
#     except Exception:
#         logger.exception("Error closing RedisManager")
#
#     logger.info("Shutdown: disposing DB engine")
#     try:
#         await dispose_db()
#     except Exception:
#         logger.exception("Error disposing DB engine")
#
#     logger.info("Shutdown finished")


async def shutdown(bot, dp):
    try:
        await dp.storage.close()
    except Exception:
        logger.exception("closing storage failed")
    try:
        await bot.session.close()
    except Exception:
        logger.exception("closing bot session failed")
    await RedisManager.close()
    await dispose_db()
    logger.info("shutdown finished")


async def run_polling():
    bot, dp = await create_bot_and_dp()
    await startup(bot, dp)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _on_sig():
        logger.info("signal received")
        stop_event.set()

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _on_sig)
        except NotImplementedError:
            pass

    polling_task = asyncio.create_task(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))
    stop_task = asyncio.create_task(stop_event.wait())

    done, pending = await asyncio.wait([polling_task, stop_task], return_when=asyncio.FIRST_COMPLETED)

    if not polling_task.done():
        try:
            await dp.stop_polling()
        except Exception:
            logger.exception("stop polling failed")

    for t in (polling_task, stop_task):
        if not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

    await shutdown(bot, dp)


if __name__ == "__main__":
    try:
        asyncio.run(run_polling())
    except KeyboardInterrupt:
        pass
