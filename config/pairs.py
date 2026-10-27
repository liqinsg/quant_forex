"""品种清单读取器 — 数据源为 config/forex_pairs.yml

- pairs:  外汇货币对（EURUSD -> EUR_USD）
- crypto: 加密货币（BTC_USD 原样保留）

输出统一转成 OANDA 格式，并去重、保持文件顺序。
"""
from pathlib import Path

import yaml

PAIRS_FILE = Path(__file__).resolve().parent / "forex_pairs.yml"

_CRYPTO_SET = None


def to_oanda(pair: str) -> str:
    """EURUSD -> EUR_USD；已含下划线（如 EUR_USD）原样返回。"""
    pair = str(pair).strip().upper()
    if "_" in pair:
        return pair
    return f"{pair[:3]}_{pair[3:]}"


def _load_section(key: str) -> list[str]:
    """读取 forex_pairs.yml 指定段，去重并转成 OANDA 格式，保持文件顺序。"""
    with open(PAIRS_FILE, encoding="utf-8") as f:
        items = (yaml.safe_load(f) or {}).get(key, []) or []

    seen, instruments = set(), []
    for pair in items:
        inst = to_oanda(pair)
        if inst not in seen:
            seen.add(inst)
            instruments.append(inst)
    return instruments


def get_instruments() -> list[str]:
    """返回去重后的 OANDA 外汇货币对列表（forex_pairs.yml 的 pairs 段）。"""
    return _load_section("pairs")


def get_crypto_instruments() -> list[str]:
    """返回去重后的 OANDA 加密货币列表（forex_pairs.yml 的 crypto 段）。"""
    return _load_section("crypto")


def get_all_instruments() -> list[str]:
    """外汇 + 加密，去重合并（供训练脚本遍历使用）。"""
    seen, merged = set(), []
    for inst in get_instruments() + get_crypto_instruments():
        if inst not in seen:
            seen.add(inst)
            merged.append(inst)
    return merged


def is_crypto(instrument: str) -> bool:
    """判断是否为加密货币品种（依据 forex_pairs.yml 的 crypto 段，结果缓存）。"""
    global _CRYPTO_SET
    if _CRYPTO_SET is None:
        _CRYPTO_SET = set(get_crypto_instruments())
    return str(instrument).strip().upper() in _CRYPTO_SET


if __name__ == "__main__":
    print(" ".join(get_instruments()))
