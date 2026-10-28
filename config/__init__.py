"""config 包 — 统一配置加载入口 + 数据/模型路径解析。

load_config() 读取 config.yaml，并把 instruments.yaml 的货币对
注入 CFG["instruments"]，因此下游代码可继续用 CFG["instruments"]。

路径按 OANDA 环境（practice / live）隔离：
    data/<env>/datasets/
    models/model_store/<env>/
"""
from pathlib import Path

import yaml

from .pairs import get_instruments, get_crypto_instruments

CONFIG_FILE = Path(__file__).resolve().parent / "config.yaml"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

REPORTS_DIR = PROJECT_ROOT / "reports"
LAST_RETRAIN_FILE = REPORTS_DIR / ".last_weekly_retrain"


def load_config() -> dict:
    """加载 config.yaml，并注入 instruments.yaml 的 instruments / crypto_instruments 列表。"""
    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["instruments"] = get_instruments()
    cfg["crypto_instruments"] = get_crypto_instruments()
    return cfg


def current_env() -> str:
    """当前 OANDA 环境：'practice' 或 'live'（由 config_oanda 解析得出）。"""
    from .config_oanda import OANDA_ENV

    return OANDA_ENV


def data_dir(env: str = None) -> Path:
    """K 线数据目录：data/<env>/datasets/。env 缺省取当前环境。"""
    return PROJECT_ROOT / "data" / (env or current_env()) / "datasets"


def model_dir(env: str = None) -> Path:
    """模型目录：models/model_store/<env>/。env 缺省取当前环境。"""
    return PROJECT_ROOT / "models" / "model_store" / (env or current_env())
