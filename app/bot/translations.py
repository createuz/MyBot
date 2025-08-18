# app/bot/translations.py
TRANSLATIONS = {
    "en": {
        "welcome": "Welcome! Choose your language:",
        "lang_set": "Language set ✅",
        "greeting": "Hello! Welcome back."
    },
    "uz": {
        "welcome": "Xush kelibsiz! Tilni tanlang:",
        "lang_set": "Til o‘zgartirildi ✅",
        "greeting": "Salom! Botga xush kelibsiz."
    },
    "ru": {
        "welcome": "Добро пожаловать! Выберите язык:",
        "lang_set": "Язык установлен ✅",
        "greeting": "Привет! Добро пожаловать."
    }
}

def t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, "")
