# run_local.py
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import start as start_pkg, callbacks as cb_pkg, lang_cmd as lang_pkg
from app.middlewares.db_middleware import DBSessionMiddleware
from app.middlewares.request_id_middleware import RequestIDMiddleware
from app.core.config import conf
from app.core.logger import get_logger
from app.db.session import init_db
from app.utils.redis_manager import RedisManager

logger = get_logger()


async def run_local():
    bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.outer_middleware(RequestIDMiddleware())
    dp.update.outer_middleware(DBSessionMiddleware())
    dp.include_router(start_pkg.router)
    dp.include_router(cb_pkg.router)
    dp.include_router(lang_pkg.router)

    await RedisManager.init()
    await init_db()

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await RedisManager.close()


if __name__ == "__main__":
    asyncio.run(run_local())
