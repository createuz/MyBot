# app/bot/handlers/start.py
from aiogram import Router, types
from aiogram.filters.command import Command
from bot.keyboards import language_keyboard
from bot.translations import t
from utils.user_service import upsert_user
from core.logger import get_logger

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message, **data):
    db = data.get("db")
    request_id = data.get("request_id")
    logger = get_logger(request_id)
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    is_premium = getattr(message.from_user, "is_premium", False)

    # 1) Create user in DB with default language 'en' (or update existing)
    try:
        user_id = await upsert_user(
            session=db,
            chat_id=tg_id,
            username=username,
            first_name=first_name,
            is_premium=is_premium,
            language="en",
            added_by=None
        )
        # commit will be attempted in middleware; but to ensure DB persistence before caching,
        # we can commit here explicitly (optional). We'll rely on middleware commit for simplicity.
        logger.info(f"User upserted in DB id={user_id} chat_id={tg_id}")
    except Exception as e:
        logger.exception(f"Failed to upsert user {tg_id}: {e}")
        await message.answer("Server error, try again later.")
        return

    # 2) Ask language selection (do NOT write to Redis yet)
    await message.answer(t("en", "welcome"), reply_markup=language_keyboard())
