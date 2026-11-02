
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
