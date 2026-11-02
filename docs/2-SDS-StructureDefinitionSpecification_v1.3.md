非常好。

现在已经从“交易策略设计”进入“系统架构设计”阶段了。

下一份文档应该不是指标、SL、TP，而是：

# Logging Schema Specification (LGS) v1.0

这是整个 v2 实验体系的核心。

原因很简单：

未来你最终能不能回答：

结构SL比ATR-SL好吗？

哪个Regime最有效？

EARLY阶段是不是比MATURE更适合结构TP？

EURUSD和GBPUSD是否有差异？

全部取决于日志有没有提前设计好。

---

# Logging Schema Specification v1.0

## 文档目标

统一所有：

研究日志

回测日志

实时日志

实验日志

统计日志

保证：

一次记录

终身可分析

---

# 日志分层

建议拆4层

L1 Signal Log

L2 Structure Log

L3 Trade Log

L4 Result Log

---

# L1 Signal Log

文件

reports/signals.jsonl

记录：

系统为什么发信号

示例：

{

  "timestamp":"2026-11-02T10:00:00Z",

  "symbol":"EUR_USD",

  "lifecycle_stage":"EARLY",

  "trend_direction":"BULL",

  "entry_probability":0.83,

  "entry_side":"BUY",

  "signal_generated":true

}

---

# L2 Structure Log

文件

reports/structure.jsonl

记录：

结构分析结果

示例

{

  "symbol":"EUR_USD",

  "sl_boundary":1.0800,

  "sl_basis":"swing_low",

  "tp1_boundary":1.0920,

  "tp1_basis":"channel_high",

  "tp2_boundary":1.1080,

  "tp2_basis":"d1_swing",

  "structure_rr":2.4,

  "market_regime":"TRENDING"

}

---

# L3 Trade Log

文件

reports/trades.jsonl

记录：

成交事实

示例：

{

  "trade_id":"EURUSD_20261102_001",

  "entry_price":1.0850,

  "entry_side":"BUY",

  "sl_boundary":1.0800,

  "tp1_boundary":1.0920,

  "tp2_boundary":1.1080,

  "experiment_group":"structural"

}

---

# L4 Result Log

文件：

reports/results.jsonl

记录：

最终结果

示例：

{

  "trade_id":"EURUSD_20261102_001",

  "trade_result":"WIN",

  "trade_exit_type":"TP1_HIT",

  "trade_duration_minutes":820,

  "trade_pnl_pips":72,

  "trade_pnl_r":2.05

}

---

# Required 字段

任何日志缺失以下字段

直接判定：

INVALID RECORD

---

## 必须字段

timestamp

symbol

experiment_group

strategy_version

---

# Recommended 字段

推荐但允许缺失

market_regime

trend_strength

lifecycle_score

structure_quality_score

---

# Optional 字段

用于未来AI分析

market_adx

market_atr20

channel_width

spread

---

# Deprecated 字段

禁止新增：

tp

sl

rr

原因：

语义不明确

统一替换：

tp1_boundary

tp2_boundary

sl_boundary

structure_rr

---

# JSONL统一索引键

未来统计最容易出问题：

symbol

timestamp

重复。

建议：

record_id

格式：

EUR_USD_20261102100000

---

# Trade ID标准

推荐：

{symbol} *{date}* {seq}

例：

EUR_USD_20261102_001

EUR_USD_20261102_002

GBP_USD_20261102_001

---

# 实验组标准

统一枚举

original

aggressive

conservative

structural

禁止：

origin

struct

testA

trial

---

# 数据质量评分

新增：

data_quality_score

计算：

Required字段完整

= 5分

Recommended完整

= 3分

Optional完整

= 2分

总分：

0~10

``

---

# 生命周期 × 结构冲突矩阵

这是 v2.2 必须要有的。

新增：

signal_structure_alignment

枚举：

ALIGNED

PARTIAL

CONFLICT

---

例如：

### ALIGNED

EARLY_BULL

TP1空间很大

TRENDING

---

### PARTIAL

DEVELOPING_BULL

TP1较近

---

### CONFLICT

EARLY_BULL

但上方D1强阻力

TP1空间极小

---

输出：

signal_structure_alignment="CONFLICT"

---

# Structure Quality Score v1.0

建议正式量化：

score =

0.35 * sl_strength +

0.30 * tp1_strength +

0.20 * tp2_strength +

0.15 * regime_score

归一：

0~10

---

Regime评分：

TRENDING   = 10

RANGING    = 6

COMPRESSED = 4

VOLATILE   = 5

---

# 研究数据库最终结构

建议：

reports/

signals.jsonl

structure.jsonl

trades.jsonl

results.jsonl

``

统计程序：

analytics/

regime_analysis.py

structure_vs_atr.py

lifecycle_analysis.py

ab_test_report.py

---

# v2.2 之前必须完成清单

## SDS

✅ Structure Definition Specification

---

## FDD

✅ Field Dictionary

---

## LGS

✅ Logging Schema

---

## RTS

下一份文档：

# Research & Testing Standard v1.0

内容包括：

A/B Test规则

样本量要求

胜率统计

收益统计

显著性检验

晋级条件

到了 RTS 完成的时候，整个 forex_oanda_v7 就已经不是一个普通 EA，而是一个完整的量化研究框架了：

Lifecycle Engine

        ↓

Structure Engine

        ↓

Logging Layer

        ↓

Research Layer

        ↓

A/B Validation

        ↓

Production Decision

这会比大多数“不断调ATR倍数”的EA工程化程度高一个层级。
