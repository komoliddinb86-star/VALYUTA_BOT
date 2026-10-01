import aiohttp
from datetime import datetime, timedelta
from config import CBU_API, CURRENCY_FLAGS


class CurrencyAPI:
    def __init__(self):
        self.cache = {}
        self.cache_time = None

    async def fetch_rates(self):
        """Markaziy Bankdan kurslarni olish (cache bilan)"""
        # Cache 1 soatdan kam bo'lsa - cache'dan qaytaramiz
        if self.cache_time and (datetime.now() - self.cache_time).seconds < 3600:
            return self.cache

        async with aiohttp.ClientSession() as session:
            async with session.get(CBU_API) as response:
                data = await response.json()

        rates = {"UZS": 1.0}
        for item in data:
            if item["Ccy"] in ["USD", "EUR", "RUB"]:
                rates[item["Ccy"]] = float(item["Rate"])

        self.cache = rates
        self.cache_time = datetime.now()
        return rates

    async def convert(self, amount: float, from_cur: str, to_cur: str):
        """Valyutani konvertatsiya qilish"""
        rates = await self.fetch_rates()
        amount_in_uzs = amount * rates[from_cur]
        result = amount_in_uzs / rates[to_cur]
        return round(result, 2)

    async def get_all_rates(self):
        """Barcha kurslarni chiroyli formatda"""
        rates = await self.fetch_rates()
        text = f"💱 *Bugungi kurslar* ({datetime.now().strftime('%d.%m.%Y')})\n\n"

        for cur in ["USD", "EUR", "RUB"]:
            flag = CURRENCY_FLAGS[cur]
            text += f"{flag} *1 {cur}* = `{rates[cur]:,.2f}` UZS\n"

        return text

    async def get_history(self, currency: str, days: int = 30):
        """Oxirgi 30 kunlik tarix"""
        history = []
        async with aiohttp.ClientSession() as session:
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                url = f"https://cbu.uz/uz/arkhiv-kursov-valyut/json/{currency}/{date}/"
                try:
                    async with session.get(url, timeout=5) as resp:
                        data = await resp.json()
                        if data:
                            history.append({
                                "date": date,
                                "rate": float(data[0]["Rate"])
                            })
                except Exception:
                    continue

        return list(reversed(history))
