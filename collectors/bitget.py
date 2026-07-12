import hashlib
import logging
import re
from typing import List

from bs4 import BeautifulSoup

from .base import BaseCollector, NewsItem

log = logging.getLogger(__name__)

# У Bitget нет официального публичного REST API для объявлений, но зато есть
# конкретный раздел Support Center — "Product updates → Futures", где
# публикуются именно нужные новости ("Bitget to adjust funding rate interval
# for..."). В отличие от прежней (неверной) попытки со страницей поиска, эта
# страница отдаёт полноценный HTML со списком статей и датами.
SECTION_URL = "https://www.bitget.com/support/sections/12508313445234"
ARTICLE_PATTERN = re.compile(r"/support/articles/(\d+)")


class BitgetCollector(BaseCollector):
    name = "Bitget"

    async def fetch(self, session) -> List[NewsItem]:
        items: List[NewsItem] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FundingRateBot/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with session.get(SECTION_URL, headers=headers, timeout=20) as resp:
                if resp.status != 200:
                    log.warning("Bitget section HTTP %s", resp.status)
                    return items
                html = await resp.text()
        except Exception as e:
            log.warning("Bitget fetch failed: %s", e)
            return items

        soup = BeautifulSoup(html, "lxml")
        seen_ids = set()
        for a in soup.find_all("a", href=True):
            m = ARTICLE_PATTERN.search(a["href"])
            if not m:
                continue
            article_id = m.group(1)
            if article_id in seen_ids:
                continue
            seen_ids.add(article_id)
            title = a.get_text(strip=True)
            if not title:
                continue
            url = a["href"]
            if url.startswith("/"):
                url = "https://www.bitget.com" + url
            items.append(
                NewsItem(
                    exchange=self.name,
                    item_id=f"bitget:{article_id}",
                    title=title,
                    description="",
                    url=url,
                    published_ts=0,
                )
            )
        if not items:
            log.warning(
                "Bitget: 0 совпадений в HTML (длина ответа: %d байт). "
                "Возможно, изменилась структура страницы — нужно перепроверить "
                "SECTION_URL/ARTICLE_PATTERN в collectors/bitget.py.",
                len(html),
            )
        return items
