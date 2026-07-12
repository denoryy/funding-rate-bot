import logging
from typing import List

from .base import BaseCollector, NewsItem

log = logging.getLogger(__name__)

# Официальный публичный эндпоинт KuCoin.
# https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-announcements
URL = "https://api.kucoin.com/api/v3/announcements"


class KucoinCollector(BaseCollector):
    name = "KuCoin"

    # Делаем отдельный запрос на каждый тип объявлений — комбинирование через
    # запятую в одном annType у KuCoin возвращало пустой список.
    ANN_TYPES = ["latest-announcements", "product-updates"]

    async def fetch(self, session) -> List[NewsItem]:
        items: List[NewsItem] = []
        seen_ids = set()
        for ann_type in self.ANN_TYPES:
            params = {
                "currentPage": 1,
                "pageSize": 50,
                "annType": ann_type,
                "lang": "en_US",
            }
            try:
                async with session.get(URL, params=params, timeout=15) as resp:
                    if resp.status != 200:
                        log.warning("KuCoin announcements HTTP %s (annType=%s)", resp.status, ann_type)
                        continue
                    data = await resp.json(content_type=None)
            except Exception as e:
                log.warning("KuCoin fetch failed (annType=%s): %s", ann_type, e)
                continue

            for art in data.get("data", {}).get("items", []):
                ann_id = art.get("annId")
                if ann_id in seen_ids:
                    continue
                seen_ids.add(ann_id)
                items.append(
                    NewsItem(
                        exchange=self.name,
                        item_id=f"kucoin:{ann_id}",
                        title=art.get("annTitle", ""),
                        description=art.get("annDesc", ""),
                        url=art.get("annUrl", ""),
                        published_ts=int(art.get("cTime", 0) or 0) // 1000,
                    )
                )
        return items
