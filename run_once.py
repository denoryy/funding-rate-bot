"""
Точка входа для запуска бота ОДИН РАЗ (проверить новости и завершиться) —
используется в GitHub Actions или в обычном cron на сервере, в отличие от
bot.py, который работает бесконечно с внутренним планировщиком.
"""
import asyncio

import aiohttp
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
from db import Database
from collectors import build_collectors
from bot import poll_once


async def main():
    config.setup_logging()

    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан (переменная окружения или .env).")
    if not config.CHAT_ID:
        raise SystemExit("CHAT_ID не задан (переменная окружения или .env).")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    db = Database(config.DB_PATH)
    collectors = build_collectors(config.EXCHANGES)
    if not collectors:
        raise SystemExit("Не выбрано ни одной валидной биржи в EXCHANGES.")

    async with aiohttp.ClientSession() as session:
        await poll_once(bot, db, collectors, session)

    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
