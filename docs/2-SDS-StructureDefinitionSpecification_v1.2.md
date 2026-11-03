这是我建议直接纳入 SDS v1.2《字段命名字典（Field Dictionary）》 的完整版本。

目标是解决未来会出现的：

entry_price
open_price
signal_price

到底哪个才是标准字段的问题。

原则：

一个概念 = 一个字段名

字段名一旦发布
禁止随意修改

13. Field Dictionary v1.2
    13.1 通用字段
    Instrument
    symbol

示例：

EUR_USD
GBP_USD
USD_JPY
XAU_USD

broker

示例：

oanda

account_id

strategy_name

示例：

lifecycle_v1
structural_v2

strategy_version

示例：

v2.1.0

structure_version

示例：

SDS_v1.2

Timestamp

统一UTC

timestamp

结构分析产生时间

signal_time

信号产生时间

entry_time

成交时间

exit_time

离场时间

13.2 生命周期字段
lifecycle_stage

枚举：

EARLY

DEVELOPING

MATURE

FADING

lifecycle_score

范围：

0~100

trend_direction

枚举：

BULL

BEAR

NEUTRAL

trend_strength

范围：

0~10

entry_probability

范围：

0.00 ~ 1.00

entry_confidence

范围：

0~10

13.3 Entry字段
entry_side

枚举：

BUY
SELL

entry_price

数据类型：

float

entry_tf

示例：

M5
M15
H1

entry_spread

单位：

pips

entry_atr

entry_reason

示例：

lifecycle_signal
structure_pullback
breakout

13.4 止损字段（SL）
sl_boundary

结构止损价格

sl_basis

枚举：

swing_low
swing_high
trendline
support
resistance
channel_boundary

sl_strength

范围：

0~10

sl_distance_price

示例：

0.0035

sl_distance_pips

示例：

35

sl_distance_atr

示例：

1.4

sl_atr_ref

观察用途

sl_hit

布尔值：

True
False

sl_hit_time

sl_reason

示例：

structural
atr_reference
manual

13.5 TP1字段
tp1_boundary

tp1_basis

枚举：

channel_high
channel_low
pivot_high
pivot_low
resistance
support

tp1_strength

tp1_distance_price

tp1_distance_pips

tp1_distance_atr

tp1_hit

tp1_hit_time

tp1_duration_minutes

13.6 TP2字段
tp2_boundary

tp2_basis

枚举：

d1_swing
d1_extension
major_resistance
major_support

tp2_strength

tp2_distance_price

tp2_distance_pips

tp2_distance_atr

tp2_hit

tp2_hit_time

13.7 Structure字段
structure_rr

计算：

(tp1_boundary - entry_price)
/
(entry_price - sl_boundary)

structure_space

价格空间

structure_quality_score

范围：

0~10

structure_confidence

范围：

0~10

structure_state

枚举：

VALID
WEAK
INVALID

13.8 Structure Source字段

用于解释来源。

sl_source_tf

示例：

M15

tp1_source_tf

示例：

H1

tp2_source_tf

示例：

D1

13.9 Fractal字段
fractal_high_price

fractal_high_time

fractal_high_strength

fractal_low_price

fractal_low_time

fractal_low_strength

13.10 Channel字段
channel_upper

channel_lower

channel_width

channel_basis

枚举：

donchian
linear_regression

13.11 Market Regime字段
market_regime

枚举：

TRENDING
RANGING
COMPRESSED
VOLATILE

market_adx

market_atr20

market_atr120

market_volatility_ratio

计算：

atr20 / atr120

13.12 Trade字段
trade_id

ticket_id

trade_status

枚举：

PENDING
OPEN
CLOSED

trade_result

枚举：

WIN
LOSS
BREAKEVEN

trade_exit_type

枚举：

SL_HIT
TP1_HIT
TP2_HIT
TIMEOUT
MANUAL

trade_duration_minutes

trade_pnl

账户货币

trade_pnl_pips

trade_pnl_r

R倍数

计算：

profit / risk

13.13 A/B Test字段

这是 v2 最重要的部分。

experiment_group

枚举：

original
aggressive
conservative
structural

baseline_sl

ATR系统SL

baseline_tp

ATR系统TP

structural_sl

结构SL

structural_tp1

结构TP1

structural_tp2

结构TP2

comparison_result

枚举：

STRUCTURE_BETTER
ATR_BETTER
SAME

13.14 JSONL 最终标准

未来 reports/lifecycle.jsonl 推荐至少输出：

{
  "symbol": "EUR_USD",
  "timestamp": "2026-11-02T10:00:00Z",

  "lifecycle_stage": "EARLY",
  "trend_direction": "BULL",

  "entry_side": "BUY",
  "entry_price": 1.0850,

  "sl_boundary": 1.0810,
  "sl_basis": "swing_low",
  "sl_strength": 8,

  "tp1_boundary": 1.0940,
  "tp1_basis": "channel_high",
  "tp1_strength": 7,

  "tp2_boundary": 1.1080,
  "tp2_basis": "d1_swing",
  "tp2_strength": 9,

  "market_regime": "TRENDING",

  "structure_rr": 2.25,
  "structure_quality_score": 8,

  "experiment_group": "structural",

  "sl_atr_ref": 1.0802,
  "tp_atr_ref": 1.0910
}

这套字段已经足够支撑：

生命周期分析
结构SL/TP分析
Regime分析
A/B测试分析
回测统计
实盘复盘
后续AI训练特征工程

再往下一步，我建议写 《Logging Schema v1.0》，把 JSONL 字段分成：

Required（必填）
Recommended（推荐）
Optional（可选）
Deprecated（废弃）

这样开发团队就不会因为字段膨胀而失

哈哈，这三个其实正好是从“设计文档”跨入“工程规范”的关键三件套。

目前 SDS v1.0 已经解决：

理念统一
↓
结构定义统一
↓
伪代码统一

下一步确实应该进入：

工程规范统一
↓
代码实现统一
↓
验证标准统一

我建议直接升级为：

Structure Definition Specification v1.1

新增三个章节：

Part 13 字段命名字典（Field Dictionary）

这是未来最容易踩坑的部分。

如果不提前规范，后期日志会出现：

tp1

tp_1

tp1_price

take_profit_1

target1

最后统计系统直接崩掉。

13.1 通用命名规则

统一采用：

<object></object>_<attribute></attribute>

例如：

sl_boundary
tp1_strength
market_regime

禁止：

boundary_sl
strength_tp1
regime_market

13.2 Entry相关
entry_price
entry_time
entry_side
entry_tf

entry_lifecycle_stage
entry_probability

示例：

{
  "entry_price":1.0845,
  "entry_side":"BUY",
  "entry_tf":"M15",
  "entry_lifecycle_stage":"EARLY",
  "entry_probability":0.73
}

13.3 SL相关
sl_boundary
sl_basis
sl_strength

sl_distance_pips
sl_distance_atr

sl_atr_ref

示例：

{
  "sl_boundary":1.0810,
  "sl_basis":"swing_low",
  "sl_strength":7,

  "sl_distance_pips":35,
  "sl_distance_atr":1.2,

  "sl_atr_ref":1.0805
}

13.4 TP1相关
tp1_boundary
tp1_basis
tp1_strength

tp1_distance_pips
tp1_distance_atr

13.5 TP2相关
tp2_boundary
tp2_basis
tp2_strength

tp2_distance_pips
tp2_distance_atr

13.6 Structure统计字段
structure_rr

structure_space

structure_quality_score

structure_version

示例：

structure_rr = 2.85

structure_space = 0.0085

structure_quality_score = 8

structure_version = "SDS_v1.1"

13.7 市场状态字段
market_regime

market_adx

market_atr20

market_atr120

13.8 回测字段
trade_outcome

trade_exit_type

trade_duration_minutes

枚举：

SL_HIT
TP1_HIT
TP2_HIT
TIMEOUT

Part 14 Python参考实现

建议直接建立：

src/

structure/
│
├── fractal.py
├── channel.py
├── regime.py
├── strength.py
├── sltp.py
└── models.py

models.py
from dataclasses import dataclass

@dataclass
class StructurePoint:
    price: float
    index: int
    timestamp: str
    strength: int

fractal.py
def find_fractal_lows(df, left=3, right=3):

    result = []

    for i in range(left, len(df)-right):

        current = df.low.iloc[i]

        left_ok = all(
            current < df.low.iloc[i-j]
            for j in range(1, left+1)
        )

        right_ok = all(
            current < df.low.iloc[i+j]
            for j in range(1, right+1)
        )

        if left_ok and right_ok:
            result.append(i)

    return result

find_fractal_highs
def find_fractal_highs(df,left=3,right=3):

    result=[]

    for i in range(left,len(df)-right):

        current=df.high.iloc[i]

        left_ok=all(
            current > df.high.iloc[i-j]
            for j in range(1,left+1)
        )

        right_ok=all(
            current > df.high.iloc[i+j]
            for j in range(1,right+1)
        )

        if left_ok and right_ok:
            result.append(i)

    return result

channel.py
def donchian_channel(df, period=50):

    upper = df.high.tail(period).max()

    lower = df.low.tail(period).min()

    return {
        "upper": upper,
        "lower": lower,
        "width": upper - lower
    }

regime.py
def classify_regime(
    adx,
    atr20,
    atr120
):

    if adx > 25:
        return "TRENDING"

    if atr20 > atr120 * 1.5:
        return "VOLATILE"

    if atr20 < atr120 * 0.8:
        return "COMPRESSED"

    return "RANGING"

sltp.py
def calculate_structural_rr(
    entry,
    sl,
    tp
):

    risk = abs(entry - sl)

    reward = abs(tp - entry)

    if risk == 0:
        return 0

    return reward / risk

Part 15 单元测试规范

这个部分非常重要。

没有测试的结构系统几乎一定会出现：

回测结果正确

实盘结果错误

15.1 Fractal测试

输入：

lows =

[10,9,8,7,5,7,8,9,10]

预期：

fractal_low_index = 4

测试：

def test_fractal_low():

    result = find_fractal_lows(df)

    assert result == [4]

15.2 Donchian测试

输入：

highs

[10,15,20,18]

lows

[5,6,8,7]

预期：

upper=20

lower=5

15.3 Market Regime测试

输入：

adx=30

atr20=0.001

atr120=0.0012

预期：

TRENDING

15.4 Structure RR测试

输入：

entry=1.1000

sl=1.0950

tp=1.1150

预期：

rr=3.0

Part 16 验收标准（Acceptance Criteria）

这是未来 GitHub Pull Request 必须满足的条件。

AC-001

Fractal识别一致性

同一数据：

100次运行

结果：

完全一致

验收：

100%

AC-002

Structure字段完整率

日志输出必须包含：

sl_boundary
sl_basis
sl_strength

tp1_boundary
tp1_basis
tp1_strength

tp2_boundary
tp2_basis
tp2_strength

验收：

> =99.9%

AC-003

程序异常率

结构计算失败：

<0.1%

AC-004

性能要求

单品种一次计算：

<100ms

目标：

<50ms

AC-005

回测兼容

新结构层关闭时：

ENABLE_STRUCTURE=false

结果：

100%等于 v1

这是最重要的一条。

我建议下一版直接升级到 v1.2

新增两个模块：

16. Lifecycle × Structure 冲突矩阵
17. Logging Schema

因为你马上会发现：

EARLY_BULL

但 TP1距离太近

怎么办？

MATURE_BULL

但 TP2很远

怎么办？

这些不是交易问题，而是系统设计问题。

如果把「冲突矩阵」和「JSONL日志标准」定义出来，你这个 forex_oanda_v7 基本就具备进入真实 AB Test（ATR vs Structural）的开发条件了。
