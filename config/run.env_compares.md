# run.env Profiles

- `run.env_original`      → Original / 平衡版（Baseline，推荐默认）
- `run.env_conservative`  → Conservative / 保守版（实盘优先）
- `run.env_aggressive`    → Aggressive / 激进版（高收益高风险）

## Quick Switch

```bash
# Original（默认）
cp run.env_original run.env

# Conservative（保守）
cp run.env_conservative run.env

# Aggressive（激进）
cp run.env_aggressive run.env
```

## Current Files

```text
config/
├── run.env
├── run.env_original
├── run.env_conservative
├── run.env_aggressive
└── run.env_compares.md
```

---

# Table of Contents

- [参数对比矩阵](#runenv-参数对比矩阵)
  - [入场筛选（Entry Filters）](#入场筛选entry-filters)
  - [信号概率门槛（Probability Thresholds）](#信号概率门槛probability-thresholds)
  - [ATR 风控设置](#atr-风控设置)
  - [加密货币过滤](#加密货币过滤)
  - [持仓控制（Exposure Control）](#持仓控制exposure-control)
  - [Core Scoring 门禁](#core-scoring-门禁)
  - [仓位与交易风格总结](#仓位与交易风格总结)
  - [OANDA 配置](#oanda-配置)
- [风险等级评估](#风险等级评估)
- [策略定位](#策略定位)
  - [Conservative](#conservative)
  - [Original](#original)
  - [Aggressive](#aggressive)
- [一句话总结](#一句话总结)

---

# run.env 参数对比矩阵

## 入场筛选（Entry Filters）

| 参数 | Aggressive | Original | Conservative |
|--------|--------:|--------:|--------:|
| MIN_GAP | 0.85 | 0.9314 | 1.10 |
| GAP_THRESHOLD | 1.2 | 1.5 | 2.0 |
| STRICT_ALIGN | 2.0 | 3.0 | 4.5 |
| ALIGN_REQUIRED | 2 | 3 | 4 |
| MAX_ENTRIES | 8 | 6 | 3 |
| MC_NEUTRAL_TP | 1.5 | 1.5 | 1.5 |
| USE_MACD | true | true | true |

### 解读

- **Aggressive**：最容易触发入场
- **Original**：平衡模式
- **Conservative**：只做最强趋势

---

## 信号概率门槛（Probability Thresholds）

| 参数 | Aggressive | Original | Conservative |
|--------|--------:|--------:|--------:|
| PROB_LONG_THRESHOLD | 0.52 | 0.55 | 0.62 |
| PROB_SHORT_THRESHOLD | 0.48 | 0.45 | 0.38 |
| CRYPTO_PROB_LONG_THRESHOLD | 0.52 | 0.55 | 0.62 |
| CRYPTO_PROB_SHORT_THRESHOLD | 0.48 | 0.45 | 0.38 |

### 解读

多头信号要求：

```text
Aggressive    52%
Original      55%
Conservative  62%
```

Conservative 只接受明显优势信号。

---

## ATR 风控设置

| 参数 | Aggressive | Original | Conservative |
|--------|--------:|--------:|--------:|
| STOP_LOSS_ATR_MULTIPLIER | 1.5 | 1.8 | 2.5 |
| TAKE_PROFIT_ATR_MULTIPLIER | 1.5 | 1.8 | 2.8 |
| CRYPTO_ATR_SL_MULTIPLIER | 2.0 | 2.5 | 3.5 |
| CRYPTO_ATR_TP_MULTIPLIER | 2.0 | 2.5 | 4.0 |

### 解读

止损空间：

```text
Aggressive  < Original < Conservative
```

Conservative 给价格更多波动空间，不容易被市场噪音扫损。

---

## 加密货币过滤

| 参数 | Aggressive | Original | Conservative |
|--------|--------:|--------:|--------:|
| CRYPTO_VOL_THRESHOLD | 0.7 | 1.0 | 1.5 |

### 解读

```text
Aggressive     接受更多高波动币种
Original       中等过滤
Conservative   只做较稳定币种
```

---

## 持仓控制（Exposure Control）

| 参数 | Aggressive | Original | Conservative |
|--------|--------:|--------:|--------:|
| MAX_ENTRIES | 8 | 6 | 3 |
| MAX_OPEN_PER_GROUP_FOREX | 8 | 6 | 3 |
| MAX_OPEN_PER_GROUP_CRYPTO | 3 | 2 | 1 |
| CROSS_MAX_NET_PER_CCY | 2 | 2 | 2 |

### 解读

```text
Aggressive   = 持仓最多
Original     = 中等
Conservative = 控仓最严格
```

---

## Core Scoring 门禁

| 参数 | Aggressive | Original | Conservative |
|--------|--------:|--------:|--------:|
| CORE_SCORE_THRESHOLD | 30 | 40 | 55 |
| CORE_GROUP_VOL_REF | 0.0020 | 0.0020 | 0.0020 |
| CORE_MAX_PER_GROUP | 2 | 1 | 1 |
| CORE_MODE | filter | filter | filter |

### 解读

组级交易门槛：

```text
Aggressive     >= 30
Original       >= 40
Conservative   >= 55
```

Conservative 会过滤掉大量低活跃度关联组。

---

## 仓位与交易风格总结

| 项目 | Aggressive | Original | Conservative |
|------|------------|-----------|--------------|
| 开仓频率 | 高 | 中 | 低 |
| 信号容忍度 | 高 | 中 | 低 |
| 趋势确认要求 | 低 | 中 | 高 |
| 最大持仓数 | 高 | 中 | 低 |
| 资金利用率 | 高 | 中 | 低 |
| 风险等级 | 高 | 中 | 低 |
| 回撤容忍度 | 高 | 中 | 低 |

---

## OANDA 配置

| 参数 | Aggressive | Original | Conservative |
|--------|--------|--------|--------|
| OANDA_ACCOUNT_ID | 101-003-39389016-005 | 101-003-39389016-005 | 101-003-39389016-005 |
| OANDA_ACCOUNT_ID_LIVE | 注释 | 001-003-21515688-002 | 001-003-21515688-002 |
| OANDA_ENV | practice | practice | practice |

---

# 风险等级评估

| 版本 | 风险 | 交易频率 | 仓位利用率 | 推荐场景 |
|--------|--------|--------|--------|--------|
| Conservative | ⭐⭐⭐ | 低 | 低 | Live 实盘 / 大资金 |
| Original | ⭐⭐⭐⭐⭐ | 中 | 中 | 默认长期运行 |
| Aggressive | ⭐⭐⭐⭐⭐⭐⭐⭐ | 高 | 高 | Demo / 牛市 / 收益优先 |

---

# 策略定位

## Conservative

```text
高门槛
少仓位
低频交易
风险最低
```

适合：

- 实盘大资金
- 长期稳健运行
- 回撤敏感账户
- 震荡市场环境

---

## Original

```text
平衡型
中等频率
中等仓位
风险收益均衡
```

适合：

- 默认配置
- 长期无人值守
- 大部分市场环境

---

## Aggressive

```text
低门槛
多仓位
高频率
收益与风险最高
```

适合：

- Demo 测试
- 牛市环境
- 收益优先策略
- 高风险承受能力账户

---

# 一句话总结

```text
Aggressive   = 宁可做错，不可错过

Original     = 风险收益平衡

Conservative = 宁可错过，不可做错
```