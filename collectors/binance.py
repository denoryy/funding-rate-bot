import logging
from typing import List

from .base import BaseCollector, NewsItem

log = logging.getLogger(__name__)

# Это НЕОФИЦИАЛЬНЫЙ endpoint, которым пользуется сам сайт Binance для страницы
# announcements. У Binance нет задокументированного публичного REST API для
# объявлений, поэтому этот адрес может измениться без предупреждения — в этом
# случае просто обновите URL/параметры здесь.
ANNOUNCEMENT_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"

# catalogId 161 = "Latest News" -> "Futures" (объявления про фьючерсы/funding).
# Можно добавить другие catalogId, чтобы расширить охват (например 48 = общие новости).
CATALOG_IDS = [161, 48]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FundingRateBot/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
    "clienttype": "web",
}


class BinanceCollector(BaseCollector):
    name = "Binance"

    async def fetch(self, session) -> List[NewsItem]:
        items: List[NewsItem] = []
        for catalog_id in CATALOG_IDS:
            params = {
                "catalogId": catalog_id,
                "pageNo": 1,
                "pageSize": 20,
            }
            try:
                async with session.get(
                    ANNOUNCEMENT_URL, params=params, headers=HEADERS, timeout=15
                ) as resp:
                    if resp.status != 200:
                        log.warning("Binance announcements HTTP %s (catalog %s)", resp.status, catalog_id)
                        continue
                    data = await resp.json(content_type=None)
            except Exception as e:
                log.warning("Binance fetch failed (catalog %s): %s", catalog_id, e)
                continue

            articles = (
                data.get("data", {}).get("catalogs", [{}])[0].get("articles", [])
                if data.get("data", {}).get("catalogs")
                else data.get("data", {}).get("articles", [])
            )
            for art in articles or []:
                code = art.get("code", "")
                title = art.get("title", "")
                item_id = f"binance:{art.get('id', code)}"
                url = f"https://www.binance.com/en/support/announcement/{code}"
                items.append(
                    NewsItem(
                        exchange=self.name,
                        item_id=item_id,
                        title=title,
                        description="",
                        url=url,
                        published_ts=int(art.get("publishDate") or art.get("releaseDate") or 0) // 1000,
                    )
                )
        return items
