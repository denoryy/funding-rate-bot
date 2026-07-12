import hashlib
import logging
import re
from typing import List

from bs4 import BeautifulSoup

from .base import BaseCollector, NewsItem

log = logging.getLogger(__name__)

# У Bitget нет официального публичного REST API для объявлений (в отличие от
# Bybit/OKX/KuCoin), поэтому здесь используется скрейпинг страницы поиска по
# Support Center. Это НЕОФИЦИАЛЬНЫЙ способ и может сломаться при редизайне
# сайта — тогда потребуется поправить SEARCH_URL/паттерн ниже.
SEARCH_URL = "https://www.bitget.com/support/search"
ARTICLE_PATTERN = re.compile(r"/support/articles/(\d+)")


class BitgetCollector(BaseCollector):
    name = "Bitget"

    async def fetch(self, session) -> List[NewsItem]:
        items: List[NewsItem] = []
        params = {"keyword": "funding rate", "lang": "en_US"}
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FundingRateBot/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with session.get(SEARCH_URL, params=params, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    log.warning("Bitget search HTTP %s", resp.status)
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
                "Вероятно, список объявлений рендерится через JavaScript и "
                "недоступен в исходном HTML — см. примечание в README про Bitget/Gate.io.",
                len(html),
            )
        return items
