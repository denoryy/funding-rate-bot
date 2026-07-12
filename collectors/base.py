from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List


@dataclass
class NewsItem:
    exchange: str          # человекочитаемое имя биржи, например "Binance"
    item_id: str           # уникальный ID для дедупликации (строка)
    title: str
    description: str
    url: str
    published_ts: int = 0  # unix timestamp, если известен


class BaseCollector(ABC):
    """Общий интерфейс для всех коллекторов объявлений биржи."""

    name: str = "base"

    @abstractmethod
    async def fetch(self, session) -> List[NewsItem]:
        """Возвращает список последних объявлений биржи (без фильтрации по теме)."""
        raise NotImplementedError
