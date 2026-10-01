import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, SUPPORTED_CURRENCIES, CURRENCY_FLAGS
from currency_api import CurrencyAPI
from chart_generator import ChartGenerator
from database import db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
api = CurrencyAPI()

# Admin ID (o'zingizning ID'ingiz)
ADMIN_IDS = [1411084303]  # ← BU YERGA O'ZINGIZNING TELEGRAM ID'INGIZNI YOZING


# ============= STATE =============
class ConvertState(StatesGroup):
    waiting_amount = State()
    from_currency = State()
    to_currency = State()


class AlertState(StatesGroup):
    currency = State()
    target_rate = State()
    condition = State()


# ============= KLAVIATURALAR =============
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💱 Kurslar"), KeyboardButton(text="🔄 Konvertatsiya")],
            [KeyboardButton(text="📈 Grafik trend"), KeyboardButton(text="📜 Tarix")],
            [KeyboardButton(text="🔔 Obuna"), KeyboardButton(text="ℹ️ Yordam")]
        ],
        resize_keyboard=True
    )


def currency_keyboard(prefix: str):
    buttons = [
        [InlineKeyboardButton(
            text=f"{CURRENCY_FLAGS[c]} {c}",
            callback_data=f"{prefix}:{c}"
        )] for c in SUPPORTED_CURRENCIES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============= /start =============
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    # Foydalanuvchini DB'ga qo'shish
    await db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or ""
    )

    text = (
        f"👋 Assalomu alaykum, *{message.from_user.first_name}*!\n\n"
        "Men — *Valyuta Konvertor Bot*man 💱\n\n"
        "*Imkoniyatlarim:*\n"
        "• 💵 Real vaqtda kurslar\n"
        "• 🔄 Konvertatsiya\n"
        "• 📈 30 kunlik trend\n"
        "• 📜 Konvertatsiya tarixi\n"
        "• 🔔 Kunlik xabarlar\n\n"
        "Quyidagi tugmalardan foydalaning 👇"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu())


# ============= KURSLAR =============
@dp.message(F.text == "💱 Kurslar")
async def show_rates(message: types.Message):
    try:
        text = await api.get_all_rates()
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")


# ============= KONVERTATSIYA =============
@dp.message(F.text == "🔄 Konvertatsiya")
async def start_convert(message: types.Message, state: FSMContext):
    await message.answer(
        "Qaysi valyutadan konvertatsiya qilmoqchisiz?",
        reply_markup=currency_keyboard("from")
    )
    await state.set_state(ConvertState.from_currency)


@dp.callback_query(F.data.startswith("from:"))
async def select_from(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split(":")[1]
    await state.update_data(from_cur=currency)
    await callback.message.edit_text(
        f"✅ {CURRENCY_FLAGS[currency]} *{currency}* tanlandi.\n\n"
        "Endi qaysi valyutaga o'tkazamiz?",
        parse_mode="Markdown",
        reply_markup=currency_keyboard("to")
    )
    await state.set_state(ConvertState.to_currency)


@dp.callback_query(F.data.startswith("to:"))
async def select_to(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split(":")[1]
    await state.update_data(to_cur=currency)
    data = await state.get_data()

    await callback.message.edit_text(
        f"💱 *{data['from_cur']}* → *{currency}*\n\n"
        "Miqdorni kiriting (faqat raqam):",
        parse_mode="Markdown"
    )
    await state.set_state(ConvertState.waiting_amount)


@dp.message(StateFilter(ConvertState.waiting_amount))
async def calculate(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri raqam kiriting!")
        return

    data = await state.get_data()
    from_cur, to_cur = data["from_cur"], data["to_cur"]

    result = await api.convert(amount, from_cur, to_cur)

    # ✅ Database'ga saqlash
    await db.add_conversion(
        user_id=message.from_user.id,
        from_cur=from_cur,
        to_cur=to_cur,
        amount=amount,
        result=result
    )

    text = (
        f"✅ *Natija:*\n\n"
        f"{CURRENCY_FLAGS[from_cur]} `{amount:,.2f}` *{from_cur}*\n"
        f"⬇️\n"
        f"{CURRENCY_FLAGS[to_cur]} `{result:,.2f}` *{to_cur}*\n\n"
        f"_💾 Tarixga saqlandi_"
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu())
    await state.clear()


# ============= TARIX =============
@dp.message(F.text == "📜 Tarix")
async def show_history(message: types.Message):
    history = await db.get_user_history(message.from_user.id, limit=10)

    if not history:
        await message.answer("📭 Sizda hali konvertatsiya tarixi yo'q.")
        return

    text = "📜 *Sizning oxirgi 10 ta konvertatsiyangiz:*\n\n"
    for i, h in enumerate(history, 1):
        from_flag = CURRENCY_FLAGS[h['from_currency']]
        to_flag = CURRENCY_FLAGS[h['to_currency']]
        date = h['created_at'][:16]  # YYYY-MM-DD HH:MM

        text += (
            f"*{i}.* {from_flag} `{h['amount']:,.2f}` {h['from_currency']} "
            f"→ {to_flag} `{h['result']:,.2f}` {h['to_currency']}\n"
            f"   _🕒 {date}_\n\n"
        )

    await message.answer(text, parse_mode="Markdown")


# ============= GRAFIK =============
@dp.message(F.text == "📈 Grafik trend")
async def trend_menu(message: types.Message):
    buttons = [
        [InlineKeyboardButton(
            text=f"{CURRENCY_FLAGS[c]} {c}",
            callback_data=f"chart:{c}"
        )] for c in ["USD", "EUR", "RUB"]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📊 Qaysi valyuta trendini ko'rmoqchisiz?", reply_markup=kb)


@dp.callback_query(F.data.startswith("chart:"))
async def show_chart(callback: types.CallbackQuery):
    currency = callback.data.split(":")[1]
    await callback.message.answer("⏳ Grafik tayyorlanmoqda...")

    history = await api.get_history(currency, days=30)
    if not history:
        await callback.message.answer("❌ Ma'lumot topilmadi.")
        return

    chart = ChartGenerator.create_trend_chart(history, currency)
    photo = BufferedInputFile(chart.read(), filename="chart.png")

    min_rate = min(h["rate"] for h in history)
    max_rate = max(h["rate"] for h in history)
    change = ((history[-1]["rate"] - history[0]["rate"]) / history[0]["rate"]) * 100

    caption = (
        f"📈 *{currency}/UZS — 30 kunlik trend*\n\n"
        f"• Eng past: `{min_rate:,.2f}` UZS\n"
        f"• Eng yuqori: `{max_rate:,.2f}` UZS\n"
        f"• O'zgarish: `{change:+.2f}%`"
    )

    await callback.message.answer_photo(photo, caption=caption, parse_mode="Markdown")


# ============= OBUNA =============
@dp.message(F.text == "🔔 Obuna")
async def subscribe(message: types.Message):
    is_active = await db.subscribe(message.from_user.id)

    if is_active:
        await message.answer(
            "✅ *Obuna bo'ldingiz!*\n"
            "Har kuni soat 09:00 da kurslarni yuboraman.",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Obuna bekor qilindi.")


# ============= YORDAM =============
@dp.message(F.text == "ℹ️ Yordam")
async def help_handler(message: types.Message):
    text = (
        "ℹ️ *Yordam*\n\n"
        "*Buyruqlar:*\n"
        "/start — Botni qayta ishga tushirish\n"
        "/stats — Statistika (admin)\n\n"
        "*Funksiyalar:*\n"
        "💱 *Kurslar* — Joriy kurslar\n"
        "🔄 *Konvertatsiya* — Valyuta o'tkazish\n"
        "📜 *Tarix* — Oxirgi 10 ta konvertatsiya\n"
        "📈 *Grafik trend* — 30 kunlik trend\n"
        "🔔 *Obuna* — Kunlik yangiliklar\n\n"
        "📊 Ma'lumotlar Markaziy Bankdan olinadi."
    )
    await message.answer(text, parse_mode="Markdown")


# ============= ADMIN: STATISTIKA =============
@dp.message(Command("stats"))
async def admin_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Bu buyruq faqat adminlar uchun.")
        return

    users_count = await db.count_users()
    subscribers = await db.get_subscribers()
    stats = await db.get_conversion_stats()

    text = (
        "📊 *Bot Statistikasi*\n\n"
        f"👥 Foydalanuvchilar: `{users_count}`\n"
        f"🔔 Obunachilar: `{len(subscribers)}`\n"
        f"🔄 Jami konvertatsiyalar: `{stats['total']}`\n"
        f"⭐ Eng mashhur valyuta: `{stats['popular_currency']}`"
    )
    await message.answer(text, parse_mode="Markdown")


# ============= KUNLIK XABAR =============
async def daily_broadcast():
    """Kunlik kurs xabarlari"""
    text = await api.get_all_rates()
    subscribers = await db.get_subscribers()

    success = 0
    failed = 0

    for user_id in subscribers:
        try:
            await bot.send_message(user_id, text, parse_mode="Markdown")
            success += 1
        except Exception as e:
            logging.error(f"Xato {user_id}: {e}")
            failed += 1

    logging.info(f"📨 Yuborildi: {success}, Xato: {failed}")


# ============= ASOSIY =============
async def main():
    # Database'ni ishga tushirish
    await db.init_db()

    # Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_broadcast, "cron", hour=9, minute=0)
    scheduler.start()

    print("🤖 Bot ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
