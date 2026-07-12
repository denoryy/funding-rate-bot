import logging

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FundingRateBot/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

# Ограничиваем длину, чтобы не тащить в память/лог огромные страницы —
# для поиска ключевых фраз про интервалы этого более чем достаточно.
MAX_CHARS = 5000


async def fetch_article_text(session, url: str) -> str:
    """Скачивает страницу объявления и возвращает извлечённый текст.
    Используется только для новостей, уже прошедших фильтр по теме
    funding rate — чтобы не делать лишних запросов на весь поток."""
    if not url:
        return ""
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as resp:
            if resp.status != 200:
                log.warning("Article fetch HTTP %s: %s", resp.status, url)
                return ""
            html = await resp.text()
    except Exception as e:
        log.warning("Article fetch failed (%s): %s", url, e)
        return ""

    try:
        soup = BeautifulSoup(html, "lxml")
        # Убираем скрипты/стили, чтобы не мешали извлечению текста
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:MAX_CHARS]
    except Exception as e:
        log.warning("Article parse failed (%s): %s", url, e)
        return ""
