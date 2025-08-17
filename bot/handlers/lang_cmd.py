# app/bot/handlers/lang_cmd.py
from aiogram import Router, types
from aiogram.filters.command import Command
from bot.keyboards import language_keyboard
from utils.redis_client import get_redis
from utils.user_service import get_user_language
from core.logger import get_logger

router = Router()

@router.message(Command("lang"))
async def lang_command(message: types.Message, **data):
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    tg_id = message.from_user.id

    redis = await get_redis()
    lang = await get_user_language(db, redis, tg_id)
    await message.answer(f"Your current language: {lang}\nChoose new:", reply_markup=language_keyboard())
