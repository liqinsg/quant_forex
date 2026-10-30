# Forex OANDA v7 — run.env 配置对比手册

## 📑 目录

- [Quick Switch — 快速切换](#quick-switch--快速切换)
- [文件结构](#文件结构)
- [参数对比矩阵](#参数对比矩阵)
  - [入场筛选 Entry Filters](#入场筛选-entry-filters)
  - [信号概率门槛 Probability Thresholds](#信号概率门槛-probability-thresholds)
  - [ATR 风控设置](#atr-风控设置)
  - [加密货币过滤](#加密货币过滤)
  - [持仓控制 Exposure Control](#持仓控制-exposure-control)
  - [Core Scoring 门禁](#core-scoring-门禁)
  - [仓位与交易风格总结](#仓位与交易风格总结)
  - [OANDA 账号配置](#oanda-账号配置)
- [风险等级评估](#风险等级评估)
- [策略定位与适用场景](#策略定位与适用场景)
  - [🔵 Conservative / 保守版](#-conservative--保守版)
  - [🟢 Original / 平衡版](#-original--平衡版)
  - [🔴 Aggressive / 激进版](#-aggressive--激进版)
- [一句话总结](#一句话总结)

---

Forex OANDA v7 — run.env 配置对比手册

## run.env Profiles

| 配置文件                 | 定位                                          |
| ------------------------ | --------------------------------------------- |
| `run.env_original`     | Original / 平衡版（Baseline，推荐默认）       |
| `run.env_conservative` | Conservative / 保守版（实盘优先，稳健）       |
| `run.env_aggressive`   | Aggressive / 激进版（高收益高风险，Demo优先） |

---

## Quick Switch — 快速切换

```bash
# Original（默认平衡版）
cp run.env_original run.env

# Conservative（保守实盘版）
cp run.env_conservative run.env

# Aggressive（激进Demo版）
cp run.env_aggressive run.env
```

---

## 文件结构

```text
config/
├── run.env                  # 当前生效配置
├── run.env_original         # 基准平衡版
├── run.env_conservative     # 保守稳健版
├── run.env_aggressive       # 激进机会版
└── run.env_compares.md      # 本对比手册
```

---

## 参数对比矩阵

### 入场筛选 Entry Filters

| 参数           | 🔴 Aggressive | 🟢 Original | 🔵 Conservative |
| -------------- | ------------: | ----------: | --------------: |
| MIN_GAP        |          0.85 |      0.9314 |            1.10 |
| GAP_THRESHOLD  |           1.2 |         1.5 |             2.0 |
| STRICT_ALIGN   |           2.0 |         3.0 |             4.5 |
| ALIGN_REQUIRED |             2 |           3 |               4 |
| MAX_ENTRIES    |             8 |           6 |               3 |
| MC_NEUTRAL_TP  |           1.5 |         1.5 |             1.5 |
| USE_MACD       |          true |        true |            true |

> **解读**：
>
> - 🔴 激进：门槛最低，最容易触发入场
> - 🟢 平衡：兼顾机会与筛选
> - 🔵 保守：只做最强趋势，严格过滤

---

### 信号概率门槛 Probability Thresholds

| 参数                        | 🔴 Aggressive | 🟢 Original | 🔵 Conservative |
| --------------------------- | ------------: | ----------: | --------------: |
| PROB_LONG_THRESHOLD         |          0.52 |        0.55 |            0.62 |
| PROB_SHORT_THRESHOLD        |          0.48 |        0.45 |            0.38 |
| CRYPTO_PROB_LONG_THRESHOLD  |          0.52 |        0.55 |            0.62 |
| CRYPTO_PROB_SHORT_THRESHOLD |          0.48 |        0.45 |            0.38 |

> **多头信号要求**：
>
> ```
> 🔴 Aggressive   ≥ 52%
> 🟢 Original     ≥ 55%
> 🔵 Conservative ≥ 62%  ← 仅接受明显优势信号
> ```
>
> 数值越高 → 信号越强、交易越少、确定性越高

---

### ATR 风控设置

| 参数                       | 🔴 Aggressive | 🟢 Original | 🔵 Conservative |
| -------------------------- | ------------: | ----------: | --------------: |
| STOP_LOSS_ATR_MULTIPLIER   |           1.5 |         1.8 |             2.5 |
| TAKE_PROFIT_ATR_MULTIPLIER |           1.5 |         1.8 |             2.8 |
| CRYPTO_ATR_SL_MULTIPLIER   |           2.0 |         2.5 |             3.5 |
| CRYPTO_ATR_TP_MULTIPLIER   |           2.0 |         2.5 |             4.0 |

> **止损空间**：
>
> ```
> 🔴 Aggressive  <  🟢 Original  <  🔵 Conservative
> 紧（快进快出）      适中           宽松（防噪音）
> ```
>
> 保守版给价格更多波动空间，避免被短期噪音误扫止损

---

### 加密货币过滤

| 参数                 | 🔴 Aggressive | 🟢 Original | 🔵 Conservative |
| -------------------- | ------------: | ----------: | --------------: |
| CRYPTO_VOL_THRESHOLD |           0.7 |         1.0 |             1.5 |

> **波动率准入**：
>
> ```
> 🔴 Aggressive   → 接受更多高波动币种
> 🟢 Original     → 中等标准
> 🔵 Conservative → 仅做稳定低波动币种
> ```
>
> 数值越高 → 允许交易的币种越少、波动越低

---

### 持仓控制 Exposure Control

| 参数                      | 🔴 Aggressive | 🟢 Original | 🔵 Conservative |
| ------------------------- | ------------: | ----------: | --------------: |
| MAX_ENTRIES               |             8 |           6 |               3 |
| MAX_OPEN_PER_GROUP_FOREX  |             8 |           6 |               3 |
| MAX_OPEN_PER_GROUP_CRYPTO |             3 |           2 |               1 |
| CROSS_MAX_NET_PER_CCY     |             2 |           2 |               2 |

> **资金占用**：
>
> ```
> 🔴 Aggressive   = 持仓上限最高，资金利用率拉满
> 🟢 Original     = 中等可控
> 🔵 Conservative = 严格控仓，单笔/整体风险最低
> ```

---

### Core Scoring 门禁

| 参数                 | 🔴 Aggressive | 🟢 Original | 🔵 Conservative |
| -------------------- | ------------: | ----------: | --------------: |
| CORE_SCORE_THRESHOLD |            30 |          40 |              55 |
| CORE_GROUP_VOL_REF   |        0.0020 |      0.0020 |          0.0020 |
| CORE_MAX_PER_GROUP   |             2 |           1 |               1 |
| CORE_MODE            |        filter |      filter |          filter |

> **组活跃度门槛**：
>
> ```
> 🔴 Aggressive   ≥ 30 → 放行更多交易组
> 🟢 Original     ≥ 40 → 常规筛选
> 🔵 Conservative ≥ 55 → 大量低波动组直接跳过
> ```
>
> 分数越高 → 只在市场明显活跃时出手

---

### 仓位与交易风格总结

| 维度         | 🔴 Aggressive | 🟢 Original | 🔵 Conservative |
| ------------ | ------------- | ----------- | --------------- |
| 开仓频率     | 高            | 中          | 低              |
| 信号容忍度   | 高            | 中          | 低              |
| 趋势确认要求 | 低            | 中          | 高              |
| 最大持仓数   | 高            | 中          | 低              |
| 资金利用率   | 高            | 中          | 低              |
| 风险等级     | 高            | 中          | 低              |
| 回撤容忍度   | 高            | 中          | 低              |

---

### OANDA 账号配置

| 参数                          | 🔴 Aggressive        | 🟢 Original          | 🔵 Conservative      |
| ----------------------------- | -------------------- | -------------------- | -------------------- |
| OANDA_ACCOUNT_ID（Demo）      | 101-003-39389016-005 | 101-003-39389016-005 | 101-003-39389016-005 |
| OANDA_ACCOUNT_ID_LIVE（实盘） | 按需配置             | 001-003-21515688-002 | 001-003-21515688-002 |
| OANDA_ENV                     | practice             | practice             | practice             |

> 💡 并行运行三套时，**请为每个配置分配独立账号ID**，避免下单冲突。

---

## 风险等级评估

| 版本            | 风险指数     | 交易频率 | 仓位利用率 | 推荐场景                         |
| --------------- | ------------ | -------- | ---------- | -------------------------------- |
| 🔵 Conservative | ⭐⭐         | 低       | 低         | 实盘 / 大资金 / 震荡市           |
| 🟢 Original     | ⭐⭐⭐⭐     | 中       | 中         | 默认长期运行 / 多数行情          |
| 🔴 Aggressive   | ⭐⭐⭐⭐⭐⭐ | 高       | 高         | Demo测试 / 强趋势行情 / 收益优先 |

---

## 策略定位与适用场景

### 🔵 Conservative / 保守版

```
高门槛 · 严筛选 · 低频出手 · 稳健优先
止损宽松 · 控仓克制 · 宁少勿滥
```

✅ 适合：

- 实盘大资金、回撤敏感账户
- 震荡/不确定市场环境
- 长期稳定运行，不追求短期暴利
- 核心理念：**宁可错过，不可做错**

---

### 🟢 Original / 平衡版

```
门槛适中 · 频率可控 · 风险收益均衡
默认基准 · 无人值守友好
```

✅ 适合：

- 默认日常运行配置
- 大部分市场环境
- 中长期稳健增值
- 核心理念：**不极端，走平衡**

---

### 🔴 Aggressive / 激进版

```
低门槛 · 高频率 · 多持仓 · 紧止损
不放过短期机会 · 接受更高波动
```

✅ 适合：

- Demo/模拟环境参数验证
- 明确趋势行情（强单边）
- 小资金、高风险承受力
- 核心理念：**宁可做错，不可错过**

---

## 一句话总结

```
🔴 Aggressive   → 机会 > 稳健
🟢 Original     → 机会 = 稳健
🔵 Conservative → 稳健 > 机会
```
