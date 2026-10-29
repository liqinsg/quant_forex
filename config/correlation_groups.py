"""关联组（correlation groups）静态定义 — v1.0

用途：拦截「同一关联组内、方向相反」的持仓冲突。
例：已持多头 EUR_USD，则本轮不再开空头 GBP_USD（两者同属 usd_foreign）。

注意：
  - 本表只负责「关联冲突判断」，与交易分组（forex / crypto，管开仓名额上限）无关；
  - 未列入本表的品种视为「组外」，一律放行；
  - 表为静态写死；将来若改为动态分组，只需替换 group_of() 的实现。
"""

# 组名 -> 成员（OANDA 格式）
CORRELATION_GROUPS = {
    # 非美货币对美元：同向 = 做空美元
    "usd_foreign": ["EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD"],
    # 日元交叉盘（是否拦截由 CORRELATION_JPY_STRICT 控制）
    "jpy_cross": [
        "USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY", "CAD_JPY", "CHF_JPY", "NZD_JPY",
    ],
    # 瑞郎报价盘（含 USD_CHF）
    "chf_quote": ["USD_CHF", "EUR_CHF", "GBP_CHF", "AUD_CHF", "CAD_CHF", "NZD_CHF"],
    # 加元报价盘（含 USD_CAD）
    "cad_quote": ["USD_CAD", "EUR_CAD", "GBP_CAD", "AUD_CAD", "NZD_CAD"],
    # 澳元/纽元报价盘（AUD_NZD 已移出至 sibling_cross）
    "aud_nzd_quote": ["EUR_AUD", "GBP_AUD", "EUR_NZD", "GBP_NZD"],
    # 兄弟互斗交叉盘：两条腿互为高相关「兄弟」货币，价格易箱体震荡
    "sibling_cross": ["EUR_GBP", "AUD_NZD"],
    # 加密（永远单列开仓名额；组内同样拦截反向冲突）
    "crypto": ["BTC_USD", "ETH_USD", "LTC_USD", "BCH_USD"],
}

# 品种 -> 组名 反查表（由 CORRELATION_GROUPS 生成）
PAIR_TO_GROUP = {
    inst: grp
    for grp, members in CORRELATION_GROUPS.items()
    for inst in members
}


def group_of(instrument):
    """返回品种所属关联组名；未纳入分组返回 None（组外一律放行）。"""
    return PAIR_TO_GROUP.get(str(instrument).strip().upper())
