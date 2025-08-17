# run.py
import asyncio

from bot.run import create_bot, on_shutdown, on_startup
from core.logger import get_logger

logger = get_logger()


async def main():
    bot, dp = await create_bot()
    try:
        await dp.start_polling(bot, on_startup=on_startup(dp),
                               on_shutdown=on_shutdown(dp))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
