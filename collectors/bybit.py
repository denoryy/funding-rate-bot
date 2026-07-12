import logging
from typing import List

from .base import BaseCollector, NewsItem

log = logging.getLogger(__name__)

# Официальный публичный эндпоинт Bybit V5, авторизация не требуется.
# https://bybit-exchange.github.io/docs/v5/announcement
URL = "https://api.bybit.com/v5/announcements/index"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bybit.com/",
    "Origin": "https://www.bybit.com",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}


class BybitCollector(BaseCollector):
    name = "Bybit"

    async def fetch(self, session) -> List[NewsItem]:
        params = {
            "locale": "en-US",
            "limit": 30,
        }
        items: List[NewsItem] = []
        try:
            async with session.get(URL, params=params, headers=HEADERS, timeout=15) as resp:
                if resp.status != 200:
                    log.warning("Bybit announcements HTTP %s", resp.status)
                    return items
                data = await resp.json(content_type=None)
        except Exception as e:
            log.warning("Bybit fetch failed: %s", e)
            return items

        result_list = data.get("result", {}).get("list", [])
        for art in result_list:
            item_id = f"bybit:{art.get('url', art.get('title'))}"
            items.append(
                NewsItem(
                    exchange=self.name,
                    item_id=item_id,
                    title=art.get("title", ""),
                    description=art.get("description", ""),
                    url=art.get("url", ""),
                    published_ts=int(art.get("dateTimestamp", 0) or 0) // 1000,
                )
            )
        return items
