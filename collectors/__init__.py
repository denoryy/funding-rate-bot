from .binance import BinanceCollector
from .bybit import BybitCollector
from .okx import OkxCollector
from .kucoin import KucoinCollector
from .bitget import BitgetCollector
from .gateio import GateioCollector

COLLECTOR_REGISTRY = {
    "binance": BinanceCollector,
    "bybit": BybitCollector,
    "okx": OkxCollector,
    "kucoin": KucoinCollector,
    "bitget": BitgetCollector,
    "gateio": GateioCollector,
}


def build_collectors(names):
    collectors = []
    for name in names:
        cls = COLLECTOR_REGISTRY.get(name)
        if cls is None:
            continue
        collectors.append(cls())
    return collectors
