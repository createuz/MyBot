# run.py
import asyncio

from bot.run import create_bot, on_shutdown, on_startup
from core.logger import get_logger

logger = get_logger()


async def main():
    bot, dp = await create_bot()
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        await dp.startup.register(on_startup(bot))
        await dp.shutdown.register(on_shutdown(bot))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
