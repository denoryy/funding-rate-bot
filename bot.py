import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from db import Database
from collectors import build_collectors
from classifier import is_funding_related, classify, detect_interval_change
from body_fetch import fetch_article_text

log = logging.getLogger("funding_bot")

SCOPE_LABEL = {
    "global": "🌐 Глобальное изменение",
    "local": "🎯 Локальное изменение (по монете/паре)",
}


def format_message(classified) -> str:
    item = classified.item
    scope_label = SCOPE_LABEL[classified.scope]
    lines = [
        f"<b>{item.exchange}</b> — {scope_label}",
        f"<b>{item.title}</b>",
    ]
    if classified.interval_change:
        lines.append(f"🔄 Смена цикла расчёта: {classified.interval_change}")
    if classified.tickers:
        lines.append("Пары: " + ", ".join(classified.tickers[:15]))
    if item.description:
        desc = item.description.strip()
        if len(desc) > 400:
            desc = desc[:400] + "…"
        lines.append(desc)
    if item.url:
        lines.append(item.url)
    return "\n\n".join(lines)


async def poll_once(bot: Bot, db: Database, collectors, session: aiohttp.ClientSession):
    for collector in collectors:
        try:
            raw_items = await collector.fetch(session)
        except Exception as e:
            log.exception("Collector %s failed: %s", collector.name, e)
            continue

        log.info("%s: fetched %d items", collector.name, len(raw_items))

        matched = 0
        already_seen = 0
        sent = 0

        for item in raw_items:
            if not is_funding_related(item):
                continue
            matched += 1

            if db.is_seen(item.item_id):
                already_seen += 1
                continue

            classified = classify(item)

            # Если в заголовке/кратком описании не нашли фразу про смену
            # цикла (from X hours to Y hours) — она может быть в теле
            # объявления, а не в кратком описании из API (актуально для
            # Binance и OKX, у которых список объявлений не отдаёт текст
            # целиком). Догружаем страницу только для уже отфильтрованных
            # новостей, чтобы не плодить лишние запросы.
            if not classified.interval_change and item.url:
                full_text = await fetch_article_text(session, item.url)
                if full_text:
                    interval_change = detect_interval_change(full_text)
                    if interval_change:
                        classified.interval_change = interval_change
                    if not item.description:
                        item.description = full_text[:400]

            text = format_message(classified)
            try:
                await bot.send_message(
                    chat_id=config.CHAT_ID,
                    text=text,
                    disable_web_page_preview=False,
                )
                log.info("Sent: [%s] %s", item.exchange, item.title)
                sent += 1
            except Exception as e:
                log.exception("Failed to send message for %s: %s", item.item_id, e)
                continue  # не помечаем как отправленное — попробуем снова в следующий цикл

            db.mark_seen(item.item_id, item.exchange, item.title, item.url)

        log.info(
            "%s: из %d новостей про funding rate — %d, уже отправлялись раньше — %d, "
            "отправлено сейчас — %d",
            collector.name, len(raw_items), matched, already_seen, sent,
        )
        if matched == 0 and raw_items:
            sample_titles = "; ".join(i.title for i in raw_items[:5])
            log.debug("%s: примеры заголовков без совпадений: %s", collector.name, sample_titles)


async def main():
    config.setup_logging()

    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан. Заполните .env (см. .env.example).")
    if not config.CHAT_ID:
        raise SystemExit("CHAT_ID не задан. Заполните .env (см. .env.example).")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    db = Database(config.DB_PATH)
    collectors = build_collectors(config.EXCHANGES)
    if not collectors:
        raise SystemExit("Не выбрано ни одной валидной биржи в EXCHANGES.")

    log.info("Запущено с биржами: %s", ", ".join(c.name for c in collectors))
    log.info("Интервал опроса: %s сек.", config.POLL_INTERVAL_SECONDS)

    async with aiohttp.ClientSession() as session:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            poll_once,
            "interval",
            seconds=config.POLL_INTERVAL_SECONDS,
            args=[bot, db, collectors, session],
            next_run_time=None,  # первый запуск делаем вручную ниже, сразу при старте
        )
        scheduler.start()

        # Первый опрос сразу при старте, не дожидаясь первого интервала
        await poll_once(bot, db, collectors, session)

        try:
            await dp.start_polling(bot)
        finally:
            scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
