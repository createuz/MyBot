# run_webhook.py
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from app.bot.handlers import start as start_pkg, callbacks as cb_pkg, lang_cmd as lang_pkg
from app.middlewares.db_middleware import DBSessionMiddleware
from app.middlewares.request_id_middleware import RequestIDMiddleware
from app.core.config import conf
from app.core.logger import get_logger
from app.db.session import init_db
from app.utils.redis_manager import RedisManager

logger = get_logger()


async def create_app():
    bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.outer_middleware(RequestIDMiddleware())
    dp.update.outer_middleware(DBSessionMiddleware())
    dp.include_router(start_pkg.router)
    dp.include_router(cb_pkg.router)
    dp.include_router(lang_pkg.router)

    await RedisManager.init()
    await init_db()

    # set webhook
    await bot.set_webhook(
        url=conf.webhook.url,
        secret_token=conf.webhook.secret,
        allowed_updates=dp.resolve_used_update_types(),
    )

    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp

    # aiogram webhook integration: use /webhook/{token} path (Telegram will send updates here)
    async def handle_update(request):
        body = await request.read()
        update = body
        # aiogram will handle it via bot
        # Simpler approach: use aiogram's built-in webhook support (not fully expanded here)
        return web.Response(text="ok")

    app.router.add_post(f"/webhook/{conf.bot.token}", handle_update)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=conf.webhook.host or "0.0.0.0", port=conf.webhook.port)
