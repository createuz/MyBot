# app/bot/translations.py
langs_text = {
    "en": {
        "welcome": "Welcome! Please choose language:",
        "greeting": "Welcome back!",
        "lang_set": "Language set."
    },
    "uz": {
        "welcome": "Xush kelibsiz! Iltimos tilni tanlang:",
        "greeting": "Xush kelibsiz!",
        "lang_set": "Til saqlandi."
    }
}


def t(lang, key):
    return langs_text.get(lang, langs_text["en"]).get(key, "")
