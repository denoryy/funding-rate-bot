import os
import logging
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "180"))
EXCHANGES = [e.strip().lower() for e in os.getenv(
    "EXCHANGES", "binance,bybit,okx,kucoin,bitget,gateio"
).split(",") if e.strip()]
DB_PATH = os.getenv("DB_PATH", "funding_bot.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Ключевые слова для фильтрации новостей о funding rate (можно расширять).
# Ищем по title + description, регистр не важен.
FUNDING_KEYWORDS = [
    "funding rate",
    "funding fee",
    "funding interval",
    "funding cap",
    "funding floor",
    "premium index",
    "interest rate",
    "financing rate",
    "mark price",
    "last price protected",
    "last price protected mechanism",
    "end last price",
    "ставк",       # рус: ставка финансирования
    "фандинг",
    "финансирован",
]

# Слова-маркеры "глобального" изменения (правило действует на всю биржу/все пары)
GLOBAL_MARKERS = [
    "all perpetual",
    "all contracts",
    "all pairs",
    "all symbols",
    "all usdt-margined",
    "all coin-margined",
    "platform-wide",
    "all futures",
    "across all",
]


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
