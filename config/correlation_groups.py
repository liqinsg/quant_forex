CORRELATION_GROUPS = {
    "usd_foreign": {"EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD"},
    "usd_base": {"USD_CHF", "USD_CAD"},
    "jpy_cross": {"USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY"},
    "crypto": {"BTC_USD", "ETH_USD"},
}
PAIR_TO_GROUP = {pair: g for g, pairs in CORRELATION_GROUPS.items() for pair in pairs}