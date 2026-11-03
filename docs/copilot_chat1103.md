
1，
今天的开发其实已经完成了。

不是客套话，是从工程角度看确实到了一个阶段性结束点。

你昨天到今天实际上完成了：

SDS v1.3
├── Fractal
├── Channel
├── Regime
├── Structure Engine
├── Logger Adapter
├── Main Loop Wiring
├── Unit Tests
├── Integration Tests
├── Lifecycle Logging
└── Production Demo Validation

而且你已经拿到了真实数据：

{
  "signal_dir": "LONG",
  "aligned": true,
  "sl_basis": "swing_low",
  "tp1_basis": "channel_high",
  "structure_version": "SDS_v1.3"
}

这不是测试桩。

这是实盘 Demo 运行出来的数据。

那今天要不要上线跑点什么？

我的答案：

要。
但不是上线新功能。

而是：

上线分析。

我认为今天最值得跑的

不是：

v2.2
v2.3

而是：

report_aligned_summary.py

然后跑：

python scripts/report_aligned_summary.py

每天生成一份统计。

因为你已经发现了一个有趣现象：

aligned=true    78

aligned=false 138

以及：

FADING

true    1
false  49

这不是小信号。

这已经开始暗示：

模型行为
≠
趋势行为

了。

真要开发的话

我只会排三个候选。

第一优先级
Phase-5 Regime Wiring

现在：

market_regime = "UNKNOWN"

全部如此。

原因我们已经知道：

Regime Engine 已完成
Regime Input 未接入

所以：

TRENDING
RANGING
EXPANDING

一个都没出来。

这是结构层目前唯一明显缺口。

第二优先级
aligned 报表

不是修改策略。

是生成：

aligned_report

比如：

aligned=true

avg_prob
avg_trend_age
avg_strength

aligned=false

avg_prob
avg_trend_age
avg_strength

看看模型到底在干什么。

第三优先级
Structure SL vs ATR SL

这个才是真正接近赚钱的东西。

例如增加：

{
  "atr_sl": ...
  "atr_sl_pips": ...

  "structure_sl": ...
  "structure_sl_pips": ...

  "delta": ...
}

然后观察：

Structure 比 ATR 远多少？
Structure 比 ATR 近多少？

我反而不建议马上做
用 Structure 替代真实止损

原因很简单。

昨天才第一次上线。

今天早上已经有：

AUD_JPY
CHF_JPY
GBP_NZD
NZD_CAD
...

的数据了。

这已经是巨大成功。

现在最贵的东西不是新代码。

而是：

真实样本

如果按交易员思路

你昨晚已经开始赚钱了。

不是账户赚钱。

是：

信息赚钱。

因为昨天以前根本不知道：

aligned
trend_stage
structure_sl
tp1

长什么样。

今天你已经知道了。

我的建议：

上午

跑：

python scripts/report_aligned_summary.py

把脚本完善好。

下午

检查：

lifecycle.jsonl

新增了多少结构记录。

今晚

让 Demo 再跑一个夜盘。

明天

拿着：

200+

条结构样本再开会。

到那时讨论：

Structure SL
Regime
Aligned Filter

就不是猜想，而是基于数据。

所以如果问我：

今天的开发完成了吗？

我的回答是：

✅ SDS v1.3 开发完成了

✅ 已经上线 Demo

✅ 已经开始产生真实结构日志

⬜ 下一阶段不是写功能

⬜ 下一阶段是让数据告诉我们下一刀该砍哪里

而且老实说，从昨晚第一批数据看，aligned / non-aligned 这条线已经开始显露价值了。 这比我原本预期来得更快。🚀

2，
先回答最重要的问题：

昨晚赚钱了吗？

不知道。

目前你贴出来的数据只能证明：

Observer 工作正常
Structure 数据已经落盘

还不能证明：

Structure 有收益

更不能证明：

系统昨晚赚钱是因为 Structure

原因很简单：

昨天上线的东西是：

ENABLE_STRUCTURE_OBSERVER

它只是：

记录

而不是：

参与下单
参与止损
参与止盈

所以：

昨晚赚了
≈ 原系统赚了

不是：

Structure Layer 赚了

而且你说得对：

昨天行情属于单边行情，一般 EA 都能赚钱

这是个很老练的判断。

如果昨晚属于：

强趋势日

那么：

顺势EA
趋势EA
突破EA

大概率都会好看。

真正有价值的不是：

盈利 +200

而是：

盈利来自哪里？

今天上线清单（我建议）

按照优先级排序：

✅ 已完成上线
SDS v1.3 Observation Layer

已经上线：

Fractal
Channel
Structure Engine
Logger Adapter
Lifecycle Integration

验证通过：

sl_boundary
tp1_boundary
aligned
trend_stage
trend_age

全部落盘成功。

✅ 今天应该上线
report_aligned_summary.py

目的：

开始分析行为

而不是：

开始改策略

重点看：

aligned=true

vs

aligned=false

✅ 今天应该跑
72小时连续观察

保持：

ENABLE_STRUCTURE_OBSERVER=true

不要关。

让它持续收集。

✅ 今天应该统计
信号方向

统计：

LONG
SHORT

占比。

aligned

统计：

aligned=true
aligned=false

占比。

stage

统计：

EARLY
DEVELOPING
MATURE
FADING

占比。

⏸️ 暂缓上线
Structure SL 实盘替代 ATR SL

不要。

现在太早。

Aligned Filter

例如：

if not aligned:
    skip()

不要。

数据还不够。

Regime Filter

例如：

if regime != TRENDING:
    skip()

不要。

因为：

market_regime
=============

UNKNOWN

接线还没完成。

我认为今天最大的发现

其实不是：

sl_boundary

而是：

aligned

你昨天统计：

aligned=true   78
aligned=false 138

以及：

FADING

true   1
false 49

这是非常有意思的现象。

翻译成人话：

趋势开始衰退时

模型经常选择反方向

这很像：

均值回归倾向

而不是：

趋势追随倾向

当然现在还不能下结论。

但已经值得跟踪。

我给今天的任务单
P0（今天必须完成）
 Structure Observer 上线
 Demo 运行
 日志验证
 report_aligned_summary.py 增强版
 输出第一份日报
P1（本周完成）
 Regime Wiring
 aligned / non-aligned 样本分析
 Structure vs ATR 距离统计
P2（下周考虑）
 Structure SL Shadow Evaluation
 Structure TP1 Shadow Evaluation
 Aligned Filter Shadow Evaluation

如果问我：

昨天最大的成果是什么？

我会回答：

不是赚钱。

而是第一次把：
趋势
结构
信号

同时记录到同一条 lifecycle 记录里。

这意味着从今天开始，你终于有能力回答：

什么样的信号最赚钱？

以前只能猜。

现在开始有数据了。🚀

3，
我觉得现在已经到一个很关键的节点了。

过去我们做的是：

记录更多字段

下一步应该升级成：

解释赚钱原因

也就是收益归因（Performance Attribution）。

目标

别只看：

本周 +3.2%

而要知道：

这3.2%是谁赚出来的？

例如：

aligned=true       +2.1R
aligned=false      -0.7R

净收益            +1.4R

那么答案就很清晰：

赚钱来自 aligned

第一版收益归因框架

我建议建立：

reports/lifecycle.jsonl
        +
reports/lifecycle_outcome.jsonl
        ↓
scripts/report_performance_attribution.py

Attribution 维度 1
aligned

最重要

输出：

ALIGNMENT ATTRIBUTION

aligned=true

count           125
win_rate        58%
avg_mfe_72h     1.42 ATR
avg_mae_72h     0.61 ATR

net_R           +23.4

---

aligned=false

count           178
win_rate        41%
avg_mfe_72h     0.82 ATR
avg_mae_72h     1.11 ATR

net_R           -17.6

立即回答：

顺势赚不赚钱
逆势赚不赚钱

Attribution 维度 2
Trend Stage
EARLY
DEVELOPING
MATURE
FADING

输出：

TREND STAGE ATTRIBUTION

EARLY
count=31
net_R=+5.3

DEVELOPING
count=98
net_R=+18.8

MATURE
count=72
net_R=-1.7

FADING
count=44
net_R=-12.9

可能直接发现：

FADING 是毒药

或者：

DEVELOPING 最赚钱

Attribution 维度 3
信号方向
LONG

SHORT

输出：

DIRECTION

LONG
count=150
net_R=+12.7

SHORT
count=102
net_R=-4.8

这经常能发现市场结构偏好。

Attribution 维度 4
概率区间

把：

prob

分桶。

例如：

0.50-0.55
0.55-0.60
0.60-0.65
0.65-0.70
0.70+

输出：

PROBABILITY ATTRIBUTION

0.50-0.55
count=80
net_R=-3.1

0.55-0.60
count=77
net_R=+1.4

0.60-0.65
count=61
net_R=+8.7

0.65-0.70
count=22
net_R=+10.1

这会直接帮助：

是否应提高阈值

Attribution 维度 5
品种

输出：

TOP CONTRIBUTORS

GBP_NZD   +8.1R
CHF_JPY   +5.3R
EUR_USD   +4.8R

BOTTOM CONTRIBUTORS

LTC_USD   -6.7R
AUD_CAD   -4.1R
NZD_CAD   -3.4R

回答：

谁在赚钱
谁在拖后腿

Attribution 维度 6
组合维度（最值钱）

这是未来的重点。

例如：

aligned=true
+
DEVELOPING

输出：

count=38
winrate=67%
net_R=+14.2

而：

aligned=false
+
FADING

输出：

count=29
winrate=21%
net_R=-10.8

这种统计极其有价值。

因为下一步你就可以做：

if aligned is False and trend_stage == "FADING":
    skip_signal()

而这已经不是拍脑袋。

是数据驱动。

生命周期设计

我建议三阶段。

Stage-1（本周）

新增：

report_aligned_summary.py

做描述统计。

Stage-2（下周）

新增：

report_performance_attribution.py

读取：

lifecycle_outcome.jsonl

生成：

WinRate
MFE
MAE
ATR Return

归因。

Stage-3

新增：

report_shadow_edge.py

专门验证：

aligned
trend_stage
regime
structure

到底有没有 Alpha。

如果让我定今天最值得开发的脚本，不是继续做策略，而是：

scripts/report_performance_attribution.py

因为从昨天开始，你已经不缺信号了。

你缺的是：

知道到底是谁在赚钱。

这才是真正的收益归因。

4，
我建议现在就把 Outcome v1.0 定下来，不然后面归因分析会一直返工。

目标很简单：

Lifecycle
记录"为什么进"

Outcome
记录"后来发生了什么"

然后两者通过：

record_id

关联。

Outcome v1.0 设计原则

不要直接记录：

赚多少钱

因为仓位、杠杆、资金管理会变。

记录：

市场给了什么机会

即：

MFE
MAE
ATR归一化收益

这样未来策略变了也能复用历史数据。

主键

直接沿用：

{
  "record_id": "CHF_JPY_2026-11-02T18:00:00+08:00"
}

Outcome v1.0
{
  "record_id": "CHF_JPY_2026-11-02T18:00:00+08:00",

  "instrument": "CHF_JPY",
  "signal_dir": "LONG",

  "entry_ts": "2026-11-02T18:00:00+08:00",
  "entry_price": 192.462,

  "atr": 0.2421,

  "close_24h": 193.015,
  "close_72h": 194.021,

  "mfe_fwd_pips": 155,
  "mae_fwd_pips": 32,

  "mfe_24h_atr": 1.82,
  "mae_24h_atr": 0.43,

  "mfe_72h_atr": 3.17,
  "mae_72h_atr": 0.91,

  "label_24h": 1,
  "label_72h": 1,

  "outcome_version": "v1.0"
}

必须保留字段
1 MFE

Maximum Favorable Excursion

"mfe_24h_atr": 1.82

表示：

未来24小时
最多曾盈利1.82 ATR

这是最重要的字段之一。

2 MAE

Maximum Adverse Excursion

"mae_24h_atr": 0.43

表示：

未来24小时
最多曾回撤0.43 ATR

3 24h 和 72h

我建议同时保留。

mfe_24h_atr
mfe_72h_atr

mae_24h_atr
mae_72h_atr

因为很多信号：

24h失败
72h成功

第二组字段

用于收益归因。

aligned

从 lifecycle 拷贝过来。

"aligned": true

这样 outcome 文件自包含。

以后分析不用 join。

trend_stage
"trend_stage": "DEVELOPING"

trend_age
"trend_age": 47

prob
"prob": 0.5695

market_regime
"market_regime": "TRENDING"

未来会启用。

我特别建议增加
structure_snapshot

直接把结构状态复制过来。

{
  "sl_basis": "swing_low",
  "sl_strength": 6,

  "tp1_basis": "channel_high",
  "tp1_strength": 0
}

这样未来即使：

lifecycle.jsonl
损坏
归档
迁移

Outcome 仍然完整。

收益归因需要哪些字段

未来脚本：

report_performance_attribution.py

其实只需要：

{
  "aligned": true,
  "trend_stage": "DEVELOPING",
  "signal_dir": "LONG",
  "prob": 0.64,

  "mfe_72h_atr": 2.3,
  "mae_72h_atr": 0.7
}

就能统计：

aligned=true

count
avg_mfe
avg_mae
edge

我建议增加一个 Shadow R

这个特别有价值。

"shadow_r": 2.46

计算：

LONG

shadow_r
========

(close_72h - entry)
/
(entry - sl_boundary)

SHORT 反向。

这样不需要真实下单。

就能回答：

如果使用 Structure SL
理论能拿到多少R

以后归因报告直接输出：

aligned=true

avg_shadow_r

和

aligned=false

avg_shadow_r

非常直观。

最终 Outcome v1.0

我会定为：

Identity
├── record_id

Signal
├── instrument
├── signal_dir
├── prob

Trend
├── aligned
├── trend_stage
├── trend_age
├── market_regime

Structure
├── sl_boundary
├── sl_basis
├── sl_strength
├── tp1_boundary
├── tp1_basis
├── tp1_strength

Outcome
├── mfe_24h_atr
├── mae_24h_atr
├── mfe_72h_atr
├── mae_72h_atr
├── shadow_r

Meta
├── atr
├── outcome_version

这套结构已经足够支撑：

aligned归因
stage归因
prob归因
instrument归因
structure归因

至少未来半年都不用再改 schema。
5，
我建议 Schema 不要一步到位搞太复杂，直接定一个 Outcome v1.0，保证未来归因分析不需要再改字段。

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",

  "$id": "https://quant-forex/schema/lifecycle_outcome_v1.json",

  "title": "Lifecycle Outcome Record",

  "type": "object",

  "required": [
    "record_id",
    "instrument",
    "signal_dir",

    "entry_ts",
    "entry_price",

    "atr",

    "aligned",
    "trend_stage",
    "trend_age",

    "prob",

    "sl_boundary",
    "sl_basis",
    "sl_strength",

    "tp1_boundary",
    "tp1_basis",
    "tp1_strength",

    "mfe_24h_atr",
    "mae_24h_atr",

    "mfe_72h_atr",
    "mae_72h_atr",

    "outcome_version"
  ],

  "properties": {
    "record_id": {
      "type": "string"
    },

    "instrument": {
      "type": "string"
    },

    "signal_dir": {
      "type": "string",
      "enum": ["LONG", "SHORT"]
    },

    "entry_ts": {
      "type": "string",
      "format": "date-time"
    },

    "entry_price": {
      "type": "number"
    },

    "atr": {
      "type": "number",
      "minimum": 0
    },

    "prob": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },

    "aligned": {
      "type": "boolean"
    },

    "trend_stage": {
      "type": "string",
      "enum": [
        "EARLY",
        "DEVELOPING",
        "MATURE",
        "FADING"
      ]
    },

    "trend_age": {
      "type": "integer",
      "minimum": 0
    },

    "market_regime": {
      "type": "string",
      "enum": [
        "TRENDING",
        "RANGING",
        "EXPANDING",
        "CONTRACTING",
        "UNKNOWN"
      ]
    },

    "sl_boundary": {
      "type": "number"
    },

    "sl_basis": {
      "type": "string"
    },

    "sl_strength": {
      "type": "integer",
      "minimum": 0
    },

    "tp1_boundary": {
      "type": "number"
    },

    "tp1_basis": {
      "type": "string"
    },

    "tp1_strength": {
      "type": "integer",
      "minimum": 0
    },

    "close_24h": {
      "type": "number"
    },

    "close_72h": {
      "type": "number"
    },

    "mfe_fwd_pips": {
      "type": "number"
    },

    "mae_fwd_pips": {
      "type": "number"
    },

    "mfe_24h_atr": {
      "type": "number"
    },

    "mae_24h_atr": {
      "type": "number"
    },

    "mfe_72h_atr": {
      "type": "number"
    },

    "mae_72h_atr": {
      "type": "number"
    },

    "shadow_r": {
      "type": "number"
    },

    "label_24h": {
      "type": "integer",
      "enum": [-1, 0, 1]
    },

    "label_72h": {
      "type": "integer",
      "enum": [-1, 0, 1]
    },

    "outcome_version": {
      "type": "string"
    }
  },

  "additionalProperties": false
}

我会把字段分层
Identity
record_id
instrument
signal_dir

Signal
prob
entry_ts
entry_price

Trend
aligned
trend_stage
trend_age
market_regime

Structure
sl_boundary
sl_basis
sl_strength

tp1_boundary
tp1_basis
tp1_strength

Outcome
mfe_24h_atr
mae_24h_atr

mfe_72h_atr
mae_72h_atr

shadow_r

Labels
label_24h
label_72h

我建议增加一个字段

未来做归因时非常好用：

"outcome_horizon": 72

这样以后扩展：

24h
72h
168h

不用改 Schema。

最关键的归因字段

如果只能保留 5 个，我选：

{
  "aligned": true,
  "trend_stage": "DEVELOPING",
  "prob": 0.64,
  "mfe_72h_atr": 2.1,
  "shadow_r": 1.7
}

仅靠这几个字段就能做：

aligned vs non-aligned
stage attribution
probability attribution
edge attribution
shadow-SL attribution

这已经足够支撑你后面要写的：

report_aligned_summary.py
report_performance_attribution.py
report_shadow_edge.py

整个 v2.1 的观察闭环。

6，
我建议校验器做成：

validators/
└── validate_lifecycle_outcome.py

特点：

✅ 校验 JSONL（一行一个 JSON）
✅ 校验必填字段
✅ 校验字段类型
✅ 校验枚举值
✅ 输出错误行号
✅ 输出错误原因
✅ 统计通过/失败数量
✅ 可接 CI

先用标准库，不引入额外依赖。

validate_lifecycle_outcome.py
#!/usr/bin/env python3

"""
Validate reports/lifecycle_outcome.jsonl

Usage:

python validators/validate_lifecycle_outcome.py 
    reports/lifecycle_outcome.jsonl
"""

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = {
    "record_id": str,
    "instrument": str,
    "signal_dir": str,

    "entry_ts": str,
    "entry_price": (int, float),

    "atr": (int, float),

    "aligned": bool,
    "trend_stage": str,
    "trend_age": int,

    "prob": (int, float),

    "sl_boundary": (int, float),
    "sl_basis": str,
    "sl_strength": int,

    "tp1_boundary": (int, float),
    "tp1_basis": str,
    "tp1_strength": int,

    "mfe_24h_atr": (int, float),
    "mae_24h_atr": (int, float),

    "mfe_72h_atr": (int, float),
    "mae_72h_atr": (int, float),

    "outcome_version": str,
}

VALID_SIGNALS = {
    "LONG",
    "SHORT",
}

VALID_STAGES = {
    "EARLY",
    "DEVELOPING",
    "MATURE",
    "FADING",
}

VALID_REGIMES = {
    "TRENDING",
    "RANGING",
    "EXPANDING",
    "CONTRACTING",
    "UNKNOWN",
}

def check_enum(record, field, allowed, errors):
    value = record.get(field)

    if value is None:
        return

    if value not in allowed:
        errors.append(
            f"{field}: invalid value '{value}'"
        )

def check_numeric_range(record, field, min_val=None, max_val=None, errors=None):
    if field not in record:
        return

    value = record[field]

    if not isinstance(value, (int, float)):
        return

    if min_val is not None and value < min_val:
        errors.append(
            f"{field}: {value} < {min_val}"
        )

    if max_val is not None and value > max_val:
        errors.append(
            f"{field}: {value} > {max_val}"
        )

def validate_record(record):
    errors = []

    #
    # required fields
    #
    for field, expected_type in REQUIRED_FIELDS.items():

        if field not in record:
            errors.append(f"missing field: {field}")
            continue

        value = record[field]

        if not isinstance(value, expected_type):
            errors.append(
                f"{field}: expected {expected_type}, "
                f"got {type(value)}"
            )

    #
    # enums
    #
    check_enum(
        record,
        "signal_dir",
        VALID_SIGNALS,
        errors,
    )

    check_enum(
        record,
        "trend_stage",
        VALID_STAGES,
        errors,
    )

    check_enum(
        record,
        "market_regime",
        VALID_REGIMES,
        errors,
    )

    #
    # probability
    #
    check_numeric_range(
        record,
        "prob",
        0.0,
        1.0,
        errors,
    )

    #
    # positive numbers
    #
    positive_fields = [
        "atr",
        "trend_age",
        "sl_strength",
        "tp1_strength",
    ]

    for field in positive_fields:

        if field not in record:
            continue

        value = record[field]

        if isinstance(value, (int, float)) and value < 0:

            errors.append(
                f"{field}: negative value {value}"
            )

    #
    # labels
    #
    for field in ("label_24h", "label_72h"):

        if field not in record:
            continue

        if record[field] not in (-1, 0, 1):

            errors.append(
                f"{field}: invalid label "
                f"{record[field]}"
            )

    return errors

def validate_jsonl(path: Path):

    total = 0
    passed = 0
    failed = 0

    with open(path, "r", encoding="utf-8") as f:

        for line_no, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            total += 1

            try:
                record = json.loads(line)

            except json.JSONDecodeError as ex:

                failed += 1

                print(
                    f"[FAIL] line={line_no} "
                    f"invalid json: {ex}"
                )

                continue

            errors = validate_record(record)

            if errors:

                failed += 1

                print(
                    f"[FAIL] line={line_no}"
                )

                for err in errors:
                    print(f"    - {err}")

            else:
                passed += 1

    print()
    print("=" * 60)

    print(f"Total  : {total}")
    print(f"Passed : {passed}")
    print(f"Failed : {failed}")

    print("=" * 60)

    return failed == 0

def main():

    if len(sys.argv) != 2:

        print(
            "Usage:\n"
            "python validate_lifecycle_outcome.py "
            "<jsonl-file></jsonl>"
        )
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():

        print(f"File not found: {path}")
        sys.exit(1)

    ok = validate_jsonl(path)

    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()

使用方法

校验 outcome：

python validators/validate_lifecycle_outcome.py 
    reports/lifecycle_outcome.jsonl

输出：

============================================================
Total  : 1285
Passed : 1285
Failed : 0
==========

或者：

[FAIL] line=312
    - prob: 1.23 > 1.0

[FAIL] line=488
    - trend_stage: invalid value 'LATE'

============================================================
Total  : 1285
Passed : 1283
Failed : 2
==========

下一步我会再加一个：

validate_lifecycle_vs_outcome.py

检查：

record_id 唯一性
record_id 是否能在 lifecycle 找到
outcome 是否存在孤儿记录

这个对后面的收益归因分析价值更大。
