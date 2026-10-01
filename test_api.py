import asyncio
from currency_api import CurrencyAPI


async def test():
    api = CurrencyAPI()

    # Kurslarni olish
    rates = await api.fetch_rates()
    print("📊 Kurslar:", rates)

    # Konvertatsiya
    result = await api.convert(100, "USD", "UZS")
    print(f"💵 100 USD = {result} UZS")


asyncio.run(test())
