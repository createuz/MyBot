# app/bot/run.py
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage  # production: RedisStorage

from app.bot.handlers import start, callbacks, lang_cmd
from app.bot.middlewares.db_middleware import DBSessionMiddleware
from app.bot.middlewares.request_id_middleware import RequestIDMiddleware
from app.core.config import conf
from app.core.logger import get_logger
from app.db.session import db
from app.utils.redis_client import get_redis, close_redis

logger = get_logger()


async def create_bot():
    bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    # middlewares
    dp.message.middleware(RequestIDMiddleware())
    dp.message.middleware(DBSessionMiddleware())
    dp.callback_query.middleware(RequestIDMiddleware())
    dp.callback_query.middleware(DBSessionMiddleware())

    # register routers
    dp.include_router(start.router)
    dp.include_router(callbacks.router)
    dp.include_router(lang_cmd.router)
    return bot, dp


async def on_startup(dispatcher):
    # init db schema for dev (in prod use alembic)
    await db.init()
    await get_redis()
    logger.info("Bot startup complete")


async def on_shutdown(dispatcher):
    # close redis and db
    await close_redis()
    await db.dispose()
    logger.info("Bot shutdown complete")
