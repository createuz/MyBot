# main.py
import asyncio
import logging
from aiohttp import web
from app.core.logger import setup_logger
from app.bot.run import create_bot  # must return (bot, dispatcher)
from app.core.config import conf
from app.web.apps import setup_aiohttp_app

logger = setup_logger()

async def run_webhook():
    bot, dp = await create_bot()
    app = await setup_aiohttp_app(bot, dp)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8443)  # TLS terminated by ingress in prod
    await site.start()
    logger.info("Webhook server started on port 8443")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested")
    finally:
        await runner.cleanup()
        await bot.session.close()

async def run_polling():
    bot, dp = await create_bot()
    try:
        # on_startup is handled by registered handlers
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested")
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass

def main():
    mode = getattr(conf, "run_mode", "polling")
    if mode == "webhook":
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())

if __name__ == "__main__":
    main()
