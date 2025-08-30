import asyncio
import signal
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import callbacks as callbacks_pkg
from app.bot.handlers import lang_cmd as lang_cmd_pkg
from app.bot.handlers import start as start_handler_pkg
from app.bot.middlewares.db_middleware import DBSessionMiddleware
from app.bot.middlewares.request_id_middleware import RequestIDMiddleware
from app.core.config import conf
from app.core.logger import get_logger
from app.db.session import init_db, dispose_db
from app.utils.redis_client import RedisManager  # keep your actual module name here

logger = get_logger()


async def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot: Bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp = Dispatcher()
    # middlewares: RequestID first, then DB session
    dp.update.outer_middleware(RequestIDMiddleware())
    dp.update.outer_middleware(DBSessionMiddleware())

    # include routers
    dp.include_router(start_handler_pkg.router)
    dp.include_router(callbacks_pkg.router)
    dp.include_router(lang_cmd_pkg.router)

    return bot, dp


async def startup_sequence(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Startup: initializing Redis")
    await RedisManager.init()
    logger.info("Startup: initializing DB (create tables if needed)")
    await init_db()
    logger.info("Startup finished")


async def shutdown_sequence(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Shutdown: closing dispatcher storage")
    try:
        await dp.storage.close()
    except Exception:
        logger.exception("Error closing dispatcher storage")

    logger.info("Shutdown: closing bot session")
    try:
        await bot.session.close()
    except Exception:
        logger.exception("Error closing bot.session")

    logger.info("Shutdown: closing Redis")
    try:
        await RedisManager.close()
    except Exception:
        logger.exception("Error closing RedisManager")

    logger.info("Shutdown: disposing DB engine")
    try:
        await dispose_db()
    except Exception:
        logger.exception("Error disposing DB engine")

    logger.info("Shutdown finished")


async def run_polling() -> None:
    bot: Optional[Bot] = None
    dp: Optional[Dispatcher] = None
    bot, dp = await create_bot_and_dispatcher()

    try:
        await startup_sequence(bot, dp)
    except Exception:
        logger.exception("Startup sequence failed — stopping")
        await shutdown_sequence(bot, dp)
        return

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _stop_on_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop_on_signal)
        except NotImplementedError:
            pass

    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))
    stop_task = asyncio.create_task(stop_event.wait())
    try:
        done, pending = await asyncio.wait([polling_task, stop_task], return_when=asyncio.FIRST_COMPLETED)
    finally:
        if not polling_task.done():
            logger.info("Stopping polling...")
            try:
                await dp.stop_polling()
            except Exception:
                logger.exception("Error while stopping polling")
        for t in (polling_task, stop_task):
            if not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
                except Exception:
                    logger.exception("Task cancel/wait error")
    await shutdown_sequence(bot, dp)


def main() -> None:
    try:
        asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — exit")
    except Exception as e:
        logger.exception("Fatal error in main: %s", e)


if __name__ == "__main__":
    main()
