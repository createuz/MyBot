# main.py
import asyncio

from app.bot.run import create_bot
from app.core.config import conf
from app.core.logger import setup_logger
from app.db.session import init_db, dispose_db
from app.utils.redis_client import init_redis, close_redis
from app.web import setup_aiohttp_app

logger = setup_logger()


async def run_polling():
    bot, dp = await create_bot()
    await init_redis()
    await init_db()
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await close_redis()
        await dispose_db()


async def run_webhook():
    bot, dp = await create_bot()
    app = await setup_aiohttp_app(bot, dp)
    # set webhook
    if conf.webhook.url and conf.webhook.secret_token:
        await bot.set_webhook(url=conf.webhook_url, secret_token=conf.webhook_secret,
                              allowed_updates=dp.resolve_used_update_types())
        logger.info("Webhook set to %s", conf.webhook.url)
    runner = None
    from aiohttp import web
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8443)  # In production, TLS via ingress
    await site.start()
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested")
    finally:
        if conf.webhook_url and conf.webhook_secret:
            try:
                await bot.delete_webhook()
            except Exception:
                logger.warning("delete_webhook failed")
        await bot.session.close()
        await close_redis()
        await dispose_db()
        if runner:
            await runner.cleanup()


def main():
    if conf.run_mode == "webhook":
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
