import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import io


class ChartGenerator:
    @staticmethod
    def create_trend_chart(history: list, currency: str):
        """30 kunlik trend grafigi"""
        dates = [datetime.strptime(h["date"], "%Y-%m-%d") for h in history]
        rates = [h["rate"] for h in history]

        # Grafik o'lchami va stili
        plt.figure(figsize=(10, 5))
        plt.style.use('seaborn-v0_8-darkgrid')

        # Chiziq chizish
        plt.plot(dates, rates, marker='o', linewidth=2,
                 color='#2E86AB', markersize=5)
        plt.fill_between(dates, rates, alpha=0.2, color='#2E86AB')

        # Sarlavha va o'qlar
        plt.title(f'{currency}/UZS — 30 kunlik trend',
                  fontsize=14, fontweight='bold')
        plt.xlabel('Sana', fontsize=11)
        plt.ylabel('Kurs (UZS)', fontsize=11)

        # Sana formati
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Rasmni xotiraga saqlash
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()

        return buf
