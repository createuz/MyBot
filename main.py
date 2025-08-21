# main.py
"""
Entrypoint for the bot using:
 - aiogram 3.22.x
 - LazySessionProxy + DBSessionMiddleware pattern
 - RedisManager singleton
 - init_db() / dispose_db() from app.db.session

How it works:
1) create Bot + Dispatcher
2) include routers (handlers)
3) register outer middlewares:
     - RequestIDMiddleware (assigns request_id to data)
     - DBSessionMiddleware (provides LazySessionProxy as data["db"])
   (Order matters: RequestID must run before DB middleware so logs have request_id)
4) init Redis and DB before polling
5) start polling; on exit do graceful cleanup
"""

import asyncio
import signal
from typing import Optional

from aiogram import Bot, Dispatcher

from app.bot.handlers import callbacks as callbacks_pkg
from app.bot.handlers import lang_cmd as lang_cmd_pkg
# routers (make sure these modules exist and export `router`)
from app.bot.handlers import start as start_handler_pkg
from app.bot.middlewares.db_middleware import DBSessionMiddleware
# middlewares
from app.bot.middlewares.request_id_middleware import RequestIDMiddleware
# app config & logging
from app.core.config import conf
from app.core.logger import get_logger
# DB init/dispose
from app.db.session import init_db, dispose_db
from app.utils.redis_client import RedisManager

# Redis manager

logger = get_logger()


async def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    """
    Create Bot and Dispatcher, register routers and middlewares.
    """
    # create bot
    bot = Bot(token=conf.bot_token, parse_mode="HTML")

    # create dispatcher
    dp = Dispatcher()

    # Register outer middlewares: RequestID first, DB session next
    dp.update.outer_middleware(RequestIDMiddleware())
    dp.update.outer_middleware(DBSessionMiddleware())

    # Include routers (handlers)
    # these modules must expose `router = Router()` as we added in patches
    dp.include_router(start_handler_pkg.router)
    dp.include_router(callbacks_pkg.router)
    dp.include_router(lang_cmd_pkg.router)

    return bot, dp


async def startup_sequence(bot: Bot, dp: Dispatcher) -> None:
    """
    Run initialization steps: redis, db etc.
    Called once before starting polling.
    """
    logger.info("Startup: initializing Redis")
    await  RedisManager.init()  # best-effort; returns None if cannot connect

    logger.info("Startup: initializing DB (create tables if needed)")
    await init_db()

    # optional: any other on-start steps can go here
    logger.info("Startup finished")


async def shutdown_sequence(bot: Bot, dp: Dispatcher) -> None:
    """
    Graceful shutdown: close storage, bot session, redis, db engine.
    """
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
    """
    High-level runner: create bot/dispatcher, init resources, start polling,
    and ensure graceful shutdown on exit.
    """
    bot: Optional[Bot] = None
    dp: Optional[Dispatcher] = None

    # Create and wire bot + dispatcher
    bot, dp = await create_bot_and_dispatcher()

    # Run startup sequence
    try:
        await startup_sequence(bot, dp)
    except Exception:
        logger.exception("Startup sequence failed — stopping")
        # If critical startup fails, try shutdown and exit
        await shutdown_sequence(bot, dp)
        return

    # Handle signals in Windows/Unix
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _stop_on_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop_on_signal)
        except NotImplementedError:
            # add_signal_handler may not be available on Windows asyncio loop
            pass

    # Start polling in background task so we can also wait for signals
    polling_task = asyncio.create_task(
        dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    )

    # Wait for either polling ends (error) or signal
    done, pending = await asyncio.wait(
        [polling_task, stop_event.wait()],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # If stop_event triggered, gracefully stop dispatcher polling
    if not polling_task.done():
        logger.info("Stopping polling...")
        try:
            await dp.stop_polling()
        except Exception:
            logger.exception("Error while stopping polling")

    # Ensure polling_task finished
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Polling task ended with exception")

    # Shutdown sequence
    await shutdown_sequence(bot, dp)


def main() -> None:
    """
    Entrypoint called when running python main.py
    """
    try:
        asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — exit")
    except Exception as e:
        logger.exception("Fatal error in main: %s", e)


if __name__ == "__main__":
    main()
