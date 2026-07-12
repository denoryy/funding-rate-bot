import logging
from typing import List

from .base import BaseCollector, NewsItem

log = logging.getLogger(__name__)

# Официальный публичный эндпоинт Bybit V5, авторизация не требуется.
# https://bybit-exchange.github.io/docs/v5/announcement
URL = "https://api.bybit.com/v5/announcements/index"


class BybitCollector(BaseCollector):
    name = "Bybit"

    async def fetch(self, session) -> List[NewsItem]:
        params = {
            "locale": "en-US",
            "limit": 30,
            # type=new_crypto|latest_bybit_news|...; оставляем пустым, чтобы получить всё,
            # фильтрация по ключевым словам funding rate идёт дальше в classifier.py
        }
        items: List[NewsItem] = []
        try:
            async with session.get(URL, params=params, timeout=15) as resp:
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
