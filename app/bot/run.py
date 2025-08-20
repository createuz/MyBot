# app/bot/run.py
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from app.bot.handlers.callbacks import router as callback_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.lang_cmd import router as lang_router
from app.bot.middlewares.db_middleware import DBSessionMiddleware
from app.bot.middlewares.request_id_middleware import RequestIDMiddleware
from app.core.config import conf
from app.core.logger import get_logger

logger = get_logger()


async def create_bot():
    bot = Bot(token=conf.bot_token, session=AiohttpSession(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    # attach handlers
    dp.include_router(start_router)
    dp.include_router(lang_router)
    dp.include_router(callback_router)
    # middlewares
    dp.update.middleware(RequestIDMiddleware())
    dp.update.middleware(DBSessionMiddleware())
    logger.info("Bot and dispatcher created")
    return bot, dp
