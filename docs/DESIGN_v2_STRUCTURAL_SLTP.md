

## ✅ 为什么 Option B 更胜一筹

| 维度                     | Option A         | Option B                                                      |
| ------------------------ | ---------------- | ------------------------------------------------------------- |
| **字段定义**       | 偏罗列、解释简略 | ✅ 清晰类型+取值规则+核心目的，拿到就能写代码                 |
| **结构判定标准化** | 提及但不够具体   | ✅ 直接写死 `left_bars=3, right_bars=3`，杜绝"一人一个写法" |
| **强度评分细则**   | 概念有但没落地   | ✅ 3分制逐条加分（共振/触碰/量能），可复现、可追溯            |
| **里程碑节奏**     | 拆得细、版本多   | ✅ 简洁三段式，重点清晰、不迷路                               |
| **整体调性**       | 技术记录         | ✅ **正式规范+团队协作文档**，任何人接手先读这个就对齐  |

一句话：**Option A 是"我想想"，Option B 是"照这个写"** —— 工程级交付，一步到位 👍

---

## 📝 正式采纳：Option B 全文纳入设计文档

直接更新 `DESIGN_v2_STRUCTURAL_SLTP.md`，下面是完整定稿版：

```markdown
# 周期结构驱动交易系统 — SL/TP 设计规范 v2.1
## 版本: v2.1 | 阶段: 观测层增强版 | 状态: 开发中
## 生效日期: 2026-11-02 | 项目: forex_oanda_v7

---

## 一、核心理念与思维边界

### 1.1 底层认知
市场本质 = **嵌套周期波动**：
- 大周期（H4/D1）→ 主趋势方向 + 终极目标
- 中周期（H1）→ 阶段确认 + 区间边界 + 中期目标
- 小周期（M15/M5）→ 精确入场 + 初始保护

SL/TP **不是比例数字**，是周期结构的自然边界：
- SL = 当前层级判断失效的位置 → 破了说明前提不成立，离场
- TP = 下一层周期结构位 → 到了说明阶段性目标达成

### 1.2 本阶段铁律 ⚠️
- ✅ Entry 完全冻结 v1：生命周期+概率模型+3基准环境不动
- ✅ 主动离场暂不开发：入场后只等SL/TP触发，不提前平、不移动保护
- 🚫 盈亏比是结果不是条件：禁止以RR为由调位；禁止固定ATR倍数思维
- 🚫 基准主循环不动：实验组独立接入、独立计算、独立对比

---

## 二、核心量化定义（杜绝主观，代码唯一）

### 2.1 Swing Low / High 判定标准
```

left_bars  = 3   # 左侧确认K线数
right_bars = 3   # 右侧确认K线数

swing_low  = 当前K线最低价 < 左右各3根的最低价
swing_high = 当前K线最高价 > 左右各3根的最高价

```
**无例外、无灵活参数**，任何人写出结果完全一致 ✅

### 2.2 结构强度评分（sl_strength / tp1_strength）
满分 3 分，逐项累加：
- +1 分｜**多周期共振**：M15结构位与H1关键位重合（误差 < 5 pips）
- +1 分｜**历史触碰**：50根K线内 ≥ 2 次有效回踩/承接
- +1 分｜**量能配合**：结构形成时成交量 > 1.5倍均量

评分含义：
- 1/3 弱结构 → 易被假突破
- 2/3 良结构 → 相对可靠
- 3/3 强结构 → 值得优先持仓

---

## 三、观测字段清单（v2.1 完整扩展）

### 原有保留 ✅
```

sl_boundary / sl_basis
tp1_boundary / tp1_basis
tp2_boundary / tp2_basis
sl_atr_ref   / tp_atr_ref

```

### 新增5大核心字段 ⭐
```

# 1️⃣ 空间分析 — 避免"方向对、没空间"

available_structure_space  # |tp1_boundary - entry_price|，单位pips
space_atr_ratio            # 空间 ÷ 当前ATR
space_category             # LOW(<0.5ATR) / MEDIUM / LARGE(>2ATR)

# 2️⃣ 市场状态 — 区分环境看效果

market_regime              # TRENDING / RANGING / VOLATILE / COMPRESSED
regime_adx                 # ADX值辅助判定
regime_band_width          # 布林带相对宽度辅助判定

# 3️⃣ 止损强度 — 防线牢不牢

sl_strength                # 1~3分，3=最强
sl_touch_count             # 该价位历史触碰次数
sl_mtf_confluence          # 是否跨周期共振 0/1

# 4️⃣ 目标强度 — 阻力/支撑重不重

tp1_strength               # 1~3分，3=最强
tp1_touch_count            # 该价位历史触碰次数
tp1_volume_cluster         # 是否成交密集区 0/1

# 5️⃣ 综合质量 — 快速筛优质机会

structure_quality_score    # 0–100，综合空间×强度×共振

```

### TP2 补充字段
```

tp2_boundary
tp2_distance_atr           # 距离换算成ATR
tp2_quality                # HIGH(<2ATR) / MEDIUM / LOW(>4ATR)

```

---

## 四、三层计算逻辑

| 层级 | 时间框架 | 输出 |
|---|---|---|
| 小周期 M15/M5 | swing判定 → 精确边界 | sl_boundary, sl_strength |
| 中周期 H1 | 通道/前高前低 → 阶段目标 | tp1_boundary, tp1_strength, market_regime |
| 大周期 H4/D1 | 波段延展 → 终极目标 | tp2_boundary, tp2_quality |

---

## 五、修正后里程碑路线

| 版本 | 内容 | 状态 | 预计 |
|---|---|---|---|
| v1.0 | Entry+生命周期+3基准对照 | ✅ 运行中 | 已上线 |
| **v2.1** | **观测层全字段接入，零侵入** | 🟡 开发中 | 2026-11-03 |
| v2.2 | structural实验组独立运行 | ⬜ 待接入 | 2026-11-05 |
| v2.3 | 样本达标 → 环境/强度/空间 全面统计 | ⬜ 待数据 | 2026-11-15 |
| v2.4 | 数据结论 → 是否替换ATR基准 | ⬜ 待定论 | 2026-11-20 |
| v3.x | 动态跟踪+主动离场（下一阶段） | ⏸️ 暂搁置 | 后续 |

---

## 六、核心原则

> **生命周期定买卖，结构边界定风险，多周期目标定收益。**  
> 不预设结构更好，只把定义写死、字段记全、环境标清 —— 让数据自己说话 ✅
```

---

## 🎯 下一步：直接落地

```bash
# 1️⃣ 保存正式版设计
nano DESIGN_v2_STRUCTURAL_SLTP.md
# 粘贴上面完整内容 → Ctrl+O → Enter → Ctrl+X

# 2️⃣ 纳入版本管理
git add DESIGN_v2_STRUCTURAL_SLTP.md
git commit -m "doc: v2.1 structural SL/TP — option B full spec adopted"
git push origin v20261028

# 3️⃣ 开始写代码：扩展 lifecycle_v1.py
# 把 swing判定 + 5大字段 + 评分逻辑 接入现有日志
```

**Option B 正式锁定为项目标准** ✅ 现在直接开始写观测层代码吗？
