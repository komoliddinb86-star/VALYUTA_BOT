import asyncio
from database import db


async def test():
    # Database yaratish
    await db.init_db()

    # Test foydalanuvchi qo'shish
    await db.add_user(123456, "test_user", "Ali")
    print("✅ Foydalanuvchi qo'shildi")

    # Foydalanuvchini olish
    user = await db.get_user(123456)
    print(f"👤 User: {user}")

    # Konvertatsiya qo'shish
    await db.add_conversion(123456, "USD", "UZS", 100, 1265000)
    print("✅ Konvertatsiya saqlandi")

    # Tarixni olish
    history = await db.get_user_history(123456)
    print(f"📜 Tarix: {history}")

    # Obuna
    result = await db.subscribe(123456)
    print(f"🔔 Obuna: {result}")

    # Statistika
    stats = await db.get_conversion_stats()
    print(f"📊 Stats: {stats}")


asyncio.run(test())
