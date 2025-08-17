# app/bot/run.py
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage  # prod -> RedisStorage

from bot.handlers import start, callbacks
from bot.handlers import lang_cmd
from bot.middlewares.db_middleware import DBSessionMiddleware
from bot.middlewares.request_id_middleware import RequestIDMiddleware
from core.config import conf
from core.logger import get_logger
from db.session import db
from utils.redis_client import get_redis, close_redis

logger = get_logger()


async def create_bot():
    bot = Bot(token=conf.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    # register middlewares
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
    # initialize DB schema (only dev). For prod use alembic migrations
    await db.init()
    await get_redis()
    logger.info("Bot startup complete")


async def on_shutdown(dispatcher):
    await close_redis()
    await db.dispose()
    logger.info("Bot shutdown complete")
