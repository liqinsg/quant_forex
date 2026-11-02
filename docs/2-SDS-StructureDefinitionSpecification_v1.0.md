
# 周期结构驱动交易系统

# Structure Definition Specification (SDS) v1.0

**项目**：`forex_oanda_v7`
**版本**：`v2.1-obs-sl-tp`
**状态**：Draft → Ready for Development
**生效日期**：2026-11-02

---

## 1. 文档目标

本规范用于统一定义：

- Structure（市场结构）
- SL Boundary（结构止损）
- TP Boundary（结构目标）
- Structure Strength（结构强度）
- Market Regime（市场状态）

确保：

> 同样的数据输入 → 任意开发者 → 任意机器 → 任意时间运行 → 输出完全一致

避免使用以下无法回测、无法验证、无法统计的主观描述：

- "重要支撑"
- "关键压力"
- "明显高点"
- "最近低点"

---

## 2. 命名规范

### 2.1 字段命名原则

统一采用 `snake_case`，例如：

- `sl_boundary`
- `tp1_boundary`
- `market_regime`
- `structure_strength`

禁止使用：

- `SLBoundary`
- `TP1Boundary`
- `MarketRegime`

### 2.2 JSON 输出标准

所有结构分析结果统一输出：

```json
{
  "symbol": "EUR_USD",
  "timestamp": "2026-11-02T08:00:00Z",
  "sl_boundary": 1.0760,
  "sl_basis": "swing_low",
  "sl_strength": 8,
  "tp1_boundary": 1.0920,
  "tp1_basis": "channel_high",
  "tp1_strength": 7,
  "tp2_boundary": 1.1080,
  "tp2_basis": "d1_swing",
  "tp2_strength": 9,
  "structure_rr": 3.0,
  "market_regime": "TRENDING",
  "sl_atr_ref": 1.0752,
  "tp_atr_ref": 1.0895
}
```

---

## 3. 时间框架定义

  周期            时间框架   职责

---

  大周期（HTF）   D1         主趋势、最终目标 TP2
  中周期（MTF）   H1         生命周期确认、通道识别、TP1 计算
  小周期（LTF）   M15        结构止损、精确入场

---

## 4. Fractal Structure 标准

### 4.1 Fractal High

定义：

```text
high[i] > high[i-1]
high[i] > high[i-2]
high[i] > high[i-3]

high[i] > high[i+1]
high[i] > high[i+2]
high[i] > high[i+3]
```

满足 `left_bars = 3`、`right_bars = 3` 时，定义：

```python
structure_type = "fractal_high"
```

### 4.2 Fractal Low

定义：

```text
low[i] < low[i-1]
low[i] < low[i-2]
low[i] < low[i-3]

low[i] < low[i+1]
low[i] < low[i+2]
low[i] < low[i+3]
```

满足条件时，定义：

```python
structure_type = "fractal_low"
```

### 4.3 输出结构

```json
{
  "type": "fractal_low",
  "price": 1.0815,
  "bar_index": 1234,
  "timestamp": "2026-11-02T01:15:00Z",
  "strength": 6
}
```

---

## 5. SL 结构规范

### 5.1 Long Position

输入：

```python
entry_side = BUY
```

搜索范围：最近 30 根 M15 K 线。

寻找最新确认的 Fractal Low，生成：

```python
sl_boundary = fractal_low.price
sl_basis = "swing_low"
```

### 5.2 空间过滤

若：

```python
(entry_price - sl_boundary) < ATR14_M15 * 0.5
```

则向前寻找上一个结构低点，直到满足：

```python
distance >= ATR14_M15 * 0.5
```

### 5.3 Short Position

在最近 30 根 M15 K 线中寻找最新确认的 Fractal High，输出：

```python
sl_basis = "swing_high"
```

---

## 6. TP1 结构规范

### 6.1 Donchian Channel

参数：

```python
period = 50
timeframe = "H1"
```

计算：

- `upper_channel`
- `lower_channel`

Long：

```python
tp1_boundary = upper_channel
tp1_basis = "channel_high"
```

Short：

```python
tp1_boundary = lower_channel
tp1_basis = "channel_low"
```

### 6.2 压缩市场 Fallback

定义：

```python
channel_width = upper_channel - lower_channel
```

若：

```python
channel_width < ATR_H1 * 1.5
```

则使用最近有效 Swing。

Long：

```python
tp1_basis = "pivot_high"
```

Short：

```python
tp1_basis = "pivot_low"
```

---

## 7. TP2 结构规范

数据范围：

```python
timeframe = "D1"
lookback = 200  # bars
```

Long：寻找范围内最高的 Fractal High，输出：

```python
tp2_boundary = highest_fractal_high
tp2_basis = "d1_swing"
```

Short：寻找范围内最低的 Fractal Low，输出：

```python
tp2_boundary = lowest_fractal_low
tp2_basis = "d1_swing"
```

---

## 8. Structure Strength 标准

### 8.1 Touch Score

  结构测试次数     Touch Score

---

  1 touch                    1
  2 touches                  2
  3 touches                  3
  4+ touches                 4

封顶：`max = 4`。

### 8.2 Timeframe Score

  时间框架     Timeframe Score

---

  M15                        1
  H1                         2
  H4                         3
  D1                         4

### 8.3 Fractal Score

  Fractal 规格     Fractal Score

---

  3x3                          1
  5x5                          2
  8x8                          3

### 8.4 最终评分

```python
raw_score = touch_score + timeframe_score + fractal_score

strength_score = round(raw_score / 11 * 10)
```

结果范围：`0–10`。

---

## 9. Structure Risk/Reward

仅作统计，不参与交易决策。

计算：

```python
tp_space = abs(tp1_boundary - entry_price)
sl_space = abs(entry_price - sl_boundary)
```

输出：

```python
structure_rr = tp_space / sl_space
```

示例：

```text
entry = 1.0800
sl    = 1.0760
tp1   = 1.0920

structure_rr = 3.0
```

---

## 10. Market Regime 规范

按以下优先级判断：

### TRENDING

条件：

```python
ADX14 > 25
```

输出：

```python
market_regime = "TRENDING"
```

### VOLATILE

条件：

```python
ATR20 > ATR120 * 1.5
```

输出：

```python
market_regime = "VOLATILE"
```

### COMPRESSED

条件：

```python
ATR20 < ATR120 * 0.8
```

输出：

```python
market_regime = "COMPRESSED"
```

### RANGING

其余情况：

```python
market_regime = "RANGING"
```

---

## 11. 生命周期兼容规范

禁止修改现有字段：

```python
trend_stage
```

现有生命周期状态保持不变：

- `EARLY`
- `DEVELOPING`
- `MATURE`
- `FADING`

仅增加以下扩展字段：

```python
sl_boundary
sl_basis
sl_strength

tp1_boundary
tp1_basis
tp1_strength

tp2_boundary
tp2_basis
tp2_strength

market_regime
structure_rr
```

兼容性要求：

- Lifecycle V1：完全兼容
- Structure Layer：作为独立附加层

---

## 12. 参考伪代码实现

### Step 1：获取结构

```python
def analyze_structure(symbol):
    ltf = load_candles(symbol, "M15")
    h1 = load_candles(symbol, "H1")
    d1 = load_candles(symbol, "D1")

    fractal_lows = detect_fractal_lows(ltf)
    fractal_highs = detect_fractal_highs(ltf)

    channel = build_donchian(h1, period=50)

    structure = {
        "fractal_lows": fractal_lows,
        "fractal_highs": fractal_highs,
        "channel": channel
    }

    return structure
```

### Step 2：计算 SL

```python
def calculate_sl(entry_side, entry_price, structure):
    if entry_side == BUY:
        swing = latest_valid_low(
            structure.fractal_lows
        )

        sl = swing.price

        while (entry_price - sl) < atr_m15 * 0.5:
            swing = previous_low(swing)
            sl = swing.price

        return sl

    else:
        swing = latest_valid_high(
            structure.fractal_highs
        )

        sl = swing.price

        while (sl - entry_price) < atr_m15 * 0.5:
            swing = previous_high(swing)
            sl = swing.price

        return sl
```

### Step 3：计算 TP1

```python
def calculate_tp1(entry_side, h1_data):
    upper = donchian_upper(h1_data)
    lower = donchian_lower(h1_data)

    width = upper - lower

    if width < atr_h1 * 1.5:
        if entry_side == BUY:
            return nearest_pivot_high()

        return nearest_pivot_low()

    if entry_side == BUY:
        return upper

    return lower
```

### Step 4：计算 TP2

```python
def calculate_tp2(entry_side, d1_data):
    swings = detect_daily_swings(d1_data)

    if entry_side == BUY:
        return highest_swing_high(
            swings,
            lookback=200
        )
    else:
        return lowest_swing_low(
            swings,
            lookback=200
        )
```

### Step 5：市场状态识别

```python
def detect_market_regime(h1):
    adx = ADX(h1, 14)
    atr20 = ATR(h1, 20)
    atr120 = ATR(h1, 120)

    if adx > 25:
        return "TRENDING"

    if atr20 > atr120 * 1.5:
        return "VOLATILE"

    if atr20 < atr120 * 0.8:
        return "COMPRESSED"

    return "RANGING"
```

---

## 13. 建议的 v2.1 最终开发顺序

### Phase A：核心引擎

先完成：

- Fractal Engine
- Donchian Engine
- Strength Engine
- Regime Engine

### Phase B：新增日志字段

新增：

- `sl_boundary`
- `tp1_boundary`
- `tp2_boundary`
- `market_regime`
- `structure_rr`

### Phase C：连续观测

观测周期：**30--90 天**。

### Phase D：统计验证

验证以下问题：

1. 结构 SL 是否降低误扫率？
2. 结构 TP 是否提高目标命中率？
3. 不同 Regime 下是否存在显著表现差异？

只有当统计结果显著优于 ATR 系统后，才进入 `v2.2 Structural Execution`
阶段。

这样能够保证整个升级路线保持：

> 可量化、可回测、可验证、可复现。

---

## 14. 开发前需明确的确定性边界

为兑现"相同输入产生完全一致输出"的目标，正式实现时还应将以下细节固定为代码级规则：

1. **K 线闭合规则**：Fractal 只能在右侧 3 根 K 线全部闭合后确认；未闭合
   K 线不得参与确认。
2. **Donchian 计算窗口**：明确当前 H1 K 线是否排除在 50
   根计算窗口之外，避免实时值变化造成结果不一致。
3. **Fractal
   并列处理**：当前定义使用严格大于/小于；相同高点或低点不构成
   Fractal。若未来改为允许相等，必须另行版本化。
4. **SL 搜索边界**：最近 30 根 M15 K
   线内找不到有效结构，或向前搜索后仍无法满足 ATR
   距离时，必须返回明确的失败状态，不得无限循环或静默改用主观价格。
5. **方向有效性**：BUY 的 SL 必须低于 entry；SELL 的 SL 必须高于
   entry。否则结构候选无效。
6. **TP 有效性**：BUY 的 TP 应高于 entry；SELL 的 TP 应低于
   entry。目标不在交易方向前方时，应定义跳过、回退或返回失败的规则。
7. **空值与异常**：数据不足、ATR 无效、除数为零、缺失 Swing
   等情况，必须有明确的状态码和日志字段。
8. **评分定义**：Touch 的容差、触碰去重间隔、Fractal 规格与评分分母 11
   的关系，应固定并纳入测试。
9. **Regime 优先级**：当多个条件同时成立时，按本规范顺序判断：TRENDING
   → VOLATILE → COMPRESSED → RANGING。
10. **数值精度**：统一价格精度、ATR 精度、比较容差和 JSON
    序列化规则，避免不同运行环境产生边界差异。

以上项目属于实现确定性所需的工程细化，不应由开发者在运行时自行发挥。
