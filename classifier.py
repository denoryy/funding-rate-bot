import re
from dataclasses import dataclass
from typing import Optional

from config import FUNDING_KEYWORDS, GLOBAL_MARKERS
from collectors.base import NewsItem

# Паттерн для поиска тикеров вида BTCUSDT, ETHUSDC, 1000PEPEUSDT и т.п.
TICKER_PATTERN = re.compile(r"\b[A-Z0-9]{2,15}(?:USDT|USDC|USD|PERP)\b")

# Числительные словами, которые биржи используют в объявлениях про интервалы
# ("every four hours" и т.п.)
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "six": 6,
    "eight": 8, "twelve": 12, "twenty-four": 24,
}

# Паттерн вида "from every four hours to every one hour" / "from 8 hours to 4 hours" /
# "from every hour to every four hours" (именно так формулируют биржи такие
# объявления — порядок всегда "from <старое> to <новое>").
_INTERVAL_CHANGE_PATTERN = re.compile(
    r"from\s+every\s+([\w\s-]+?)\s+to\s+every\s+([\w\s-]+?)(?=[.,;\n]|$)",
    re.IGNORECASE,
)

# Запасной паттерн для формулировки БЕЗ "from" — так пишет, например, Gate.io:
# "GATE will adjust the funding interval ... to every 1 hour" или
# "...funding rate execution frequency ... to every 8 hours" (без указания
# исходного интервала в самом тексте).
_INTERVAL_TARGET_ONLY_PATTERN = re.compile(
    r"(?:funding\s+interval|execution\s+frequency|settlement\s+frequency)"
    r".{0,80}?\bto\s+every\s+([\w\s-]+?)\s*hours?",
    re.IGNORECASE | re.DOTALL,
)


def _parse_hours(phrase: str) -> Optional[int]:
    """Парсит фразу вида 'four hours', '8 hours' или просто 'hour' (без
    числа — подразумевается 1) в количество часов."""
    tokens = [t for t in phrase.strip().lower().split() if t not in ("hour", "hours")]
    if not tokens:
        # Была голая "hour"/"hours" без числа — подразумевается "раз в час"
        return 1
    token = tokens[0]
    if token.isdigit():
        return int(token)
    return _NUMBER_WORDS.get(token)


@dataclass
class ClassifiedNews:
    item: NewsItem
    scope: str          # "global" | "local"
    tickers: list
    interval_change: Optional[str] = None  # человекочитаемое описание смены цикла, если есть


def is_funding_related(item: NewsItem) -> bool:
    text = f"{item.title} {item.description}".lower()
    return any(keyword.lower() in text for keyword in FUNDING_KEYWORDS)


def detect_interval_change(text: str) -> Optional[str]:
    """Ищет в тексте фразу вида 'from every N hours to every M hours' и
    определяет направление: переход на более длинный (старший) цикл расчёта
    funding rate или на более короткий (младший)."""
    # Биржи иногда пишут "hourly" вместо "every hour" — приводим к общему виду.
    normalized = re.sub(r"\bhourly\b", "every hour", text, flags=re.IGNORECASE)

    match = _INTERVAL_CHANGE_PATTERN.search(normalized)
    if match:
        old_hours = _parse_hours(match.group(1))
        new_hours = _parse_hours(match.group(2))
        if old_hours is not None and new_hours is not None and old_hours != new_hours:
            if new_hours > old_hours:
                direction = "⬆️ переход на СТАРШИЙ цикл (реже)"
            else:
                direction = "⬇️ переход на МЛАДШИЙ цикл (чаще)"
            return f"{old_hours}ч → {new_hours}ч ({direction})"

    # Не нашли "from X to Y" — пробуем запасной паттерн без "from" (Gate.io и
    # похожие формулировки). В этом случае исходный интервал неизвестен, так
    # что направление (старше/младше) указать не можем — сообщаем только
    # целевое значение.
    fallback_match = _INTERVAL_TARGET_ONLY_PATTERN.search(normalized)
    if fallback_match:
        new_hours = _parse_hours(fallback_match.group(1) + " hours")
        if new_hours is not None:
            return f"→ {new_hours}ч (исходный интервал не указан в тексте)"

    return None


def classify(item: NewsItem) -> ClassifiedNews:
    text = f"{item.title} {item.description}"
    lowered = text.lower()

    tickers = sorted(set(TICKER_PATTERN.findall(text.upper())))

    is_global = any(marker in lowered for marker in GLOBAL_MARKERS)
    # Если явных маркеров "глобально" нет, но и тикеры не упомянуты —
    # тоже считаем изменение потенциально глобальным (например, объявление
    # про новую формулу без перечисления конкретных пар).
    if not is_global and not tickers:
        is_global = True

    scope = "global" if is_global else "local"
    interval_change = detect_interval_change(text)
    return ClassifiedNews(item=item, scope=scope, tickers=tickers, interval_change=interval_change)
