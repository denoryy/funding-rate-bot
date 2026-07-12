import logging
from typing import List

from .base import BaseCollector, NewsItem

log = logging.getLogger(__name__)

# Официальный публичный эндпоинт OKX V5.
# https://www.okx.com/docs-v5/en/#support-announcements
URL = "https://www.okx.com/api/v5/support/announcements"


class OkxCollector(BaseCollector):
    name = "OKX"

    async def fetch(self, session) -> List[NewsItem]:
        items: List[NewsItem] = []
        # У OKX объявления разбиты на категории (annType). Изменения формулы
        # funding rate публикуются в категории "Derivatives" — это видно по
        # структуре их Support Center: Support center → Announcements →
        # Derivatives (slug: announcements-derivatives). Дополнительно берём
        # "Trading updates" и общий список последних объявлений — для более
        # широкого охвата на случай, если что-то попадёт в другую категорию.
        params_list = [
            {"annType": "announcements-derivatives"},
            {"annType": "announcements-trading-updates"},
            {},
        ]
        headers = {"Accept-Language": "en-US,en;q=0.9"}
        seen_urls = set()
        for params in params_list:
            try:
                async with session.get(URL, params=params, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        log.warning("OKX announcements HTTP %s (params=%s)", resp.status, params)
                        continue
                    data = await resp.json(content_type=None)
            except Exception as e:
                log.warning("OKX fetch failed (params=%s): %s", params, e)
                continue

            for block in data.get("data", []):
                for art in block.get("details", []):
                    url = art.get("url", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    item_id = f"okx:{url or art.get('title')}"
                    items.append(
                        NewsItem(
                            exchange=self.name,
                            item_id=item_id,
                            title=art.get("title", ""),
                            description="",
                            url=url,
                            published_ts=int(art.get("pTime", 0) or 0) // 1000,
                        )
                    )
        return items
