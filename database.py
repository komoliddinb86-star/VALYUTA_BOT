import aiosqlite
from datetime import datetime
from typing import Optional


class Database:
    def __init__(self, db_path: str = "currency_bot.db"):
        self.db_path = db_path

    async def init_db(self):
        """Database va jadvallarni yaratish"""
        async with aiosqlite.connect(self.db_path) as db:
            # Foydalanuvchilar jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)

            # Konvertatsiya tarixi
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    from_currency TEXT NOT NULL,
                    to_currency TEXT NOT NULL,
                    amount REAL NOT NULL,
                    result REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Obunalar
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    notify_time TEXT DEFAULT '09:00',
                    is_active BOOLEAN DEFAULT 1,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Kurs ogohlantirishlari
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    target_rate REAL NOT NULL,
                    condition TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            await db.commit()
            print("✅ Database tayyor!")

    # ==================== USERS ====================
    async def add_user(self, user_id: int, username: str, first_name: str):
        """Yangi foydalanuvchi qo'shish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            """, (user_id, username, first_name))
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[dict]:
        """Foydalanuvchini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_users(self) -> list:
        """Barcha faol foydalanuvchilar"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE is_active = 1"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def count_users(self) -> int:
        """Foydalanuvchilar soni"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return row[0]

    # ==================== CONVERSIONS ====================
    async def add_conversion(self, user_id: int, from_cur: str,
                             to_cur: str, amount: float, result: float):
        """Konvertatsiyani saqlash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO conversions 
                (user_id, from_currency, to_currency, amount, result)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, from_cur, to_cur, amount, result))
            await db.commit()

    async def get_user_history(self, user_id: int, limit: int = 10) -> list:
        """Foydalanuvchining konvertatsiya tarixi"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM conversions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_conversion_stats(self) -> dict:
        """Umumiy statistika"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM conversions")
            total = (await cursor.fetchone())[0]

            cursor = await db.execute("""
                SELECT from_currency, COUNT(*) as cnt 
                FROM conversions 
                GROUP BY from_currency 
                ORDER BY cnt DESC 
                LIMIT 1
            """)
            popular = await cursor.fetchone()

            return {
                "total": total,
                "popular_currency": popular[0] if popular else "Yo'q"
            }

    # ==================== SUBSCRIPTIONS ====================
    async def subscribe(self, user_id: int) -> bool:
        """Obuna bo'lish"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT is_active FROM subscriptions WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()

            if row is None:
                # Yangi obuna
                await db.execute(
                    "INSERT INTO subscriptions (user_id) VALUES (?)",
                    (user_id,)
                )
                await db.commit()
                return True
            else:
                # Holatni o'zgartirish (toggle)
                new_status = 0 if row[0] else 1
                await db.execute(
                    "UPDATE subscriptions SET is_active = ? WHERE user_id = ?",
                    (new_status, user_id)
                )
                await db.commit()
                return bool(new_status)

    async def is_subscribed(self, user_id: int) -> bool:
        """Obuna holatini tekshirish"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT is_active FROM subscriptions WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return bool(row[0]) if row else False

    async def get_subscribers(self) -> list:
        """Barcha obunachilarni olish"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id FROM subscriptions WHERE is_active = 1"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    # ==================== ALERTS ====================
    async def add_alert(self, user_id: int, currency: str,
                        target_rate: float, condition: str):
        """Kurs ogohlantirish qo'shish (condition: 'above' yoki 'below')"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO alerts (user_id, currency, target_rate, condition)
                VALUES (?, ?, ?, ?)
            """, (user_id, currency, target_rate, condition))
            await db.commit()

    async def get_user_alerts(self, user_id: int) -> list:
        """Foydalanuvchi ogohlantirishlari"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM alerts 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_active_alerts(self) -> list:
        """Barcha faol ogohlantirishlar"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM alerts WHERE is_active = 1"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def deactivate_alert(self, alert_id: int):
        """Ogohlantirishni o'chirish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE alerts SET is_active = 0 WHERE id = ?",
                (alert_id,)
            )
            await db.commit()


# Global instance
db = Database()
