# # run.py
#
# # run.py
# import asyncio
#
# from app.bot.run import create_bot, on_startup, on_shutdown
# from app.core.logger import get_logger
#
# logger = get_logger()
#
#
# async def main():
#     bot, dp = await create_bot()
#     try:
#         await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
#         await dp.startup.register(on_startup(bot))
#         await dp.shutdown.register(on_shutdown(bot))
#     except (KeyboardInterrupt, SystemExit):
#         logger.info("Shutdown requested")
#     finally:
#         await bot.session.close()
#
#
# if __name__ == "__main__":
#     asyncio.run(main())


import asyncio

from app.bot.run import create_bot, on_startup, on_shutdown  # yoki create_bot() qaytaradigan funksiya
from app.core.logger import get_logger

logger = get_logger()


async def main():
    bot, dp = await create_bot()
    await bot.send_message(chat_id=5383531061, text="<b>✅ Bot ishga tushdi...</b>")

    # wrapperlar: dispatcher ni on_startup/on_shutdown ga uzatish uchun
    async def _on_startup():
        # on_startup olishi kerak bo'lgan dispatcherni beramiz
        await on_startup(dp)

    async def _on_shutdown():
        await on_shutdown(dp)

    try:
        # use resolve_used_update_types() to only receive updates your handlers expect
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            on_startup=_on_startup,
            on_shutdown=_on_shutdown,
            # optionally skip old updates on restart:
            skip_updates=True
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested")
    finally:
        # always try to close bot session and free resources
        try:
            await bot.session.close()
        except Exception as e:
            logger.warning("Failed to close bot.session: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
