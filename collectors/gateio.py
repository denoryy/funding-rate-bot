import logging
import re
from typing import List

from bs4 import BeautifulSoup

from .base import BaseCollector, NewsItem

log = logging.getLogger(__name__)

# У Gate.io тоже нет официального публичного REST API для объявлений, но
# зато есть отдельная категория "Fees" в Announcement Center, где публикуются
# именно нужные новости — "Adjusting the Funding Rate Execution Frequency",
# "Adjusting the Funding Rate Interval" и т.п. Это гораздо точнее и надёжнее,
# чем скрейпить общую ленту всех объявлений.
ANNOUNCEMENTS_URL = "https://www.gate.com/en/announcements/fee"
ARTICLE_PATTERN = re.compile(r"/announcements/article/(\d+)")


class GateioCollector(BaseCollector):
    name = "Gate.io"

    async def fetch(self, session) -> List[NewsItem]:
        items: List[NewsItem] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FundingRateBot/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with session.get(ANNOUNCEMENTS_URL, headers=headers, timeout=25) as resp:
                if resp.status != 200:
                    log.warning("Gate.io announcements HTTP %s", resp.status)
                    return items
                html = await resp.text()
        except Exception as e:
            log.warning("Gate.io fetch failed: %s", e)
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
                url = "https://www.gate.com" + url
            items.append(
                NewsItem(
                    exchange=self.name,
                    item_id=f"gateio:{article_id}",
                    title=title,
                    description="",
                    url=url,
                    published_ts=0,
                )
            )
        if not items:
            log.warning(
                "Gate.io: 0 совпадений в HTML (длина ответа: %d байт). "
                "Вероятно, список объявлений рендерится через JavaScript и "
                "недоступен в исходном HTML — см. примечание в README про Bitget/Gate.io.",
                len(html),
            )
        return items
