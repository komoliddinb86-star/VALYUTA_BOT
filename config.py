import os
from dotenv import load_dotenv

# .env faylni yuklash
load_dotenv()

# Bot tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN topilmadi! .env faylni tekshiring.")

# Markaziy Bank API
CBU_API = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"

# Qo'llab-quvvatlanadigan valyutalar
SUPPORTED_CURRENCIES = ["USD", "EUR", "RUB", "UZS"]

# Bayroqlar
CURRENCY_FLAGS = {
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "RUB": "🇷🇺",
    "UZS": "🇺🇿"
}
