"""货币对清单读取器 — 数据源为 config/forex_pairs.yml

输出统一转成 OANDA 格式（EURUSD -> EUR_USD），并去重、保持文件顺序。
"""
from pathlib import Path

import yaml

PAIRS_FILE = Path(__file__).resolve().parent / "forex_pairs.yml"


def to_oanda(pair: str) -> str:
    """EURUSD -> EUR_USD；已含下划线（如 EUR_USD）原样返回。"""
    pair = str(pair).strip().upper()
    if "_" in pair:
        return pair
    return f"{pair[:3]}_{pair[3:]}"


def get_instruments() -> list[str]:
    """返回去重后的 OANDA 货币对列表，顺序与 forex_pairs.yml 一致。"""
    with open(PAIRS_FILE, encoding="utf-8") as f:
        pairs = yaml.safe_load(f).get("pairs", [])

    seen, instruments = set(), []
    for pair in pairs:
        inst = to_oanda(pair)
        if inst not in seen:
            seen.add(inst)
            instruments.append(inst)
    return instruments


if __name__ == "__main__":
    print(" ".join(get_instruments()))
