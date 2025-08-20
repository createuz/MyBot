# app/bot/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def language_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="English", callback_data="lang:en"),
         InlineKeyboardButton(text="O'zbek", callback_data="lang:uz")]
    ])
    return kb
