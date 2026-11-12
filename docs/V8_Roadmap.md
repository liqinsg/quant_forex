#docs/V8_Roadmap.md

# Quant Forex V8 Evolution Roadmap

Version: V8.0
 Status: Planning
 Strategy: Incremental Evolution
 Principle: Observe → Validate → Deploy → Measure → Iterate

Background

Current V7 architecture:

Market Data
    ↓
Feature Engine
    ↓
Per-Pair LGB Model
    ↓
Risk Gate
    ↓
Correlation Gate
    ↓
Core Group Gate
    ↓
Position Manager
    ↓
OANDA Execution

Current strengths:

Per-pair ML models
OANDA execution abstraction
ATR-based SL/TP
Correlation risk controls
Structure Engine framework
Lifecycle logging
Dry-run support
Outcome attribution foundation

Current weaknesses:

Problem #1

Trend signals often enter too late.

Current features rely heavily on:

EMA
MACD
ATR

These are lagging indicators.

Result:

Direction correct
Entry timing poor
Risk-reward ratio deteriorates

Problem #2

Range-bound markets repeatedly trigger stop-losses.

Typical sequence:

Breakout
 ↓
Open Long
 ↓
Retrace
 ↓
Stop Loss
 ↓
Breakout again
 ↓
Repeat

Result:

Whipsaw losses

Problem #3

Exit logic remains primitive.

Current:

SL = ATR * N
TP = ATR * M

This assumes all markets behave similarly.

Reality:

EURUSD ≠ GBPJPY
GBPJPY ≠ AUDNZD
AUDNZD ≠ BTCUSD

V8 Vision

Move beyond:

Predict Direction

Toward:

Predict Direction
Predict Entry Quality
Predict Exit Potential
Adapt To Regime

V8.1 Pair Profile Engine

Priority:

★★★★★

Risk:

Low

Deployment:

Observe Only

Objective

Different instruments have different personalities.

Examples:

EURUSD  → Mean Reversion
GBPJPY  → Momentum
AUDNZD  → Channel
USDJPY  → Breakout
BTCUSD  → Volatility Expansion

Current V7 treats all instruments similarly.

Deliverables
New File
config/pair_profiles.yaml

Example:

default:
  style: unknown

EUR_USD:
  style: mean_reversion

GBP_JPY:
  style: momentum

AUD_NZD:
  style: channel

USD_JPY:
  style: breakout

BTC_USD:
  style: volatility

New Module
config/pair_profiles.py

Functions:

load_pair_profiles()

get_pair_profile(instrument)

get_pair_style(instrument)

Lifecycle Extension

Append:

{
  "pair_profile":"mean_reversion"
}

No trading changes.

Acceptance Criteria

Must NOT change:

Signal Generation
Risk Gate
SL/TP
Position Sizing
Execution

Only observation.

V8.2 Regime Engine

Priority:

★★★★★

Deployment:

Observe Only

Objective

Classify market condition.

Output:

TREND
RANGE
VOLATILE
TRANSITION

Inputs

Existing:

ADX
ATR20
ATR120
EMA20
EMA50

Structure Framework:

compute_regime_inputs()

Output

Lifecycle log:

{
  "regime":"RANGE"
}

Goal

Answer:

What environment am I trading in?

Not:

Should I buy?

V8.3 Structure Score

Priority:

★★★★★

Deployment:

Observe Only

Objective

Convert structure analysis into a score.

Sources:

aligned
channel
fractal
regime

Formula

Initial version:

structure_score = (
    aligned_score
    +
    channel_score
    +
    fractal_score
) / 3

Range:

0.0 ~ 1.0

Output
{
  "structure_score":0.82
}

Observation Stage

Duration:

2 Weeks

Goal:

Collect attribution data.

Build Reports

New scripts:

scripts/report_pair_profile.py
scripts/report_regime.py
scripts/report_structure_score.py

Metrics:

Signal Count
Win Rate
Profit Factor
Expectancy
Average Hold Time
MFE
MAE

V8.4 Entry Quality Model

Priority:

★★★★★

Deployment:

Research

Objective

Predict:

Is this a good entry location?

Instead of:

Will price eventually go up?

Labels

Generate:

future_mfe
future_mae

Model:

entry_model.pkl

Output:

entry_score

Range:

0.0 ~ 1.0

V8.5 TP Prediction Model

Priority:

★★★★★★★★

Deployment:

Research

Objective

Replace:

ATR × N

With:

Expected MFE

Training Target
future_max_favorable_excursion

Output:

expected_tp

V8.6 Adaptive SL

Priority:

★★★

Deployment:

Research

Objective

Prevent premature stop-outs.

Current issue:

Correct direction
Wrong stop placement

Rule

Never allow:

SL < ATR Floor

Example:

SL =
max(
    ATR * 1.5,
    expected_pullback
)

Deployment Process

Every phase follows:

Step 1

Develop

Feature
Unit Test

Step 2

Dry Run

python main_loop_v2.py --dry-run

Duration:

24 hours

Step 3

Demo Account

Duration:

7 days

Step 4

Analyze

Generate:

Win Rate
PF
Expectancy
MFE
MAE

Step 5

Promotion

Only after statistics confirm improvement.

Success Criteria

V8 succeeds if:

Whipsaw losses reduce

AND

Average MFE captured increases

AND

Profit Factor improves

without increasing drawdown

V8.1 Code Skeleton

目录结构：

config/
├── pair_profiles.yaml
└── pair_profiles.py

tests/
└── test_pair_profiles.py

scripts/
└── report_pair_profile.py

config/pair_profiles.yaml
default:
  style: unknown

EUR_USD:
  style: mean_reversion

GBP_USD:
  style: momentum

AUD_USD:
  style: mean_reversion

USD_JPY:
  style: breakout

GBP_JPY:
  style: momentum

AUD_JPY:
  style: momentum

AUD_NZD:
  style: channel

BTC_USD:
  style: volatility

ETH_USD:
  style: volatility

config/pair_profiles.py
from pathlib import Path

import yaml

_PROFILE_CACHE = None

def load_pair_profiles():

    global _PROFILE_CACHE

    if _PROFILE_CACHE is not None:
        return _PROFILE_CACHE

    cfg_file = (
        Path(__file__).parent
        / "pair_profiles.yaml"
    )

    with open(cfg_file, "r") as f:
        _PROFILE_CACHE = yaml.safe_load(f)

    return _PROFILE_CACHE

def get_pair_profile(instrument):

    profiles = load_pair_profiles()

    profile = profiles.get(
        instrument,
        profiles.get("default", {})
    )

    return profile

def get_pair_style(instrument):

    profile = get_pair_profile(
        instrument
    )

    return profile.get(
        "style",
        "unknown"
    )

tests/test_pair_profiles.py
from config.pair_profiles import (
    get_pair_style,
)

def test_known_pair():

    style = get_pair_style(
        "EUR_USD"
    )

    assert style == "mean_reversion"

def test_unknown_pair():

    style = get_pair_style(
        "XYZ_ABC"
    )

    assert style == "unknown"

scripts/report_pair_profile.py
import json
from collections import Counter

counter = Counter()

with open(
    "reports/lifecycle.jsonl"
) as f:

    for line in f:

        row = json.loads(line)

        profile = row.get(
            "pair_profile",
            "unknown"
        )

        counter[profile] += 1

print("\nSignals per Profile\n")

for k, v in sorted(
    counter.items()
):
    print(f"{k:20} {v}")

analyze_cycle() 接入点

新增：

from config.pair_profiles import (
    get_pair_style
)

在 _write_lc() 前：

pair_style = get_pair_style(inst)

写入 lifecycle：

extra = extra or {}

extra["pair_profile"] = pair_style

这样 V8.1 完全符合：

Observe Only
Zero Trading Impact
Easy Rollback
Easy Validation

先完成 V8.1，再进入 V8.2 Regime Engine。这样每一步都能量化验证收益归因。
