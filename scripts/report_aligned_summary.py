#!/usr/bin/env python3

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

LIFECYCLE_FILE = Path("reports/lifecycle.jsonl")


def load_rows(path):
    rows = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    return rows


def align_key(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    return "null"


def prob_bucket(prob):
    if prob is None:
        return "unknown"

    if prob < 0.40:
        return "<40%"

    if prob < 0.50:
        return "40-50%"

    if prob < 0.60:
        return "50-60%"

    if prob < 0.70:
        return "60-70%"

    if prob < 0.80:
        return "70-80%"

    return ">=80%"


def main():
    rows = load_rows(LIFECYCLE_FILE)

    print("=" * 70)
    print("ALIGNED SUMMARY REPORT")
    print("=" * 70)

    aligned_counter = Counter()

    stage_counter = defaultdict(Counter)

    direction_counter = Counter()
    direction_align_counter = defaultdict(Counter)

    prob_dist = defaultdict(Counter)

    inst_counter = defaultdict(Counter)

    prob_true = []
    prob_false = []

    for r in rows:

        aligned = align_key(r.get("aligned"))
        stage = r.get("trend_stage", "UNKNOWN")
        direction = r.get("signal_dir", "NEUTRAL")
        prob = r.get("prob")

        aligned_counter[aligned] += 1

        stage_counter[stage][aligned] += 1

        direction_counter[direction] += 1
        direction_align_counter[aligned][direction] += 1

        bucket = prob_bucket(prob)
        prob_dist[bucket][aligned] += 1

        inst = r.get("instrument", "UNKNOWN")
        inst_counter[inst][aligned] += 1

        if aligned == "true" and prob is not None:
            prob_true.append(prob)

        elif aligned == "false" and prob is not None:
            prob_false.append(prob)

    total = sum(aligned_counter.values())

    #
    # ALIGNMENT
    #
    print("\n[ALIGNMENT]")

    for k in ("true", "false", "null"):
        n = aligned_counter[k]
        pct = n * 100 / total if total else 0

        print(f"{k:>5}: {n:>6} ({pct:6.2f}%)")

    #
    # TREND STAGE
    #
    print("\n[TREND STAGE]")
    print(
        f"{'stage':<12}"
        f"{'true':>8}"
        f"{'false':>8}"
        f"{'null':>8}"
    )

    for stage in sorted(stage_counter.keys()):

        c = stage_counter[stage]

        print(
            f"{stage:<12}"
            f"{c['true']:>8}"
            f"{c['false']:>8}"
            f"{c['null']:>8}"
        )

    #
    # DIRECTION
    #
    print("\n[DIRECTION]")

    for direction, count in direction_counter.most_common():
        print(f"{direction:<10} {count:>6}")

    #
    # ALIGNMENT x DIRECTION
    #
    print("\n[ALIGNMENT x DIRECTION]")

    for aligned in ("true", "false", "null"):

        print(f"\n{aligned}")

        dirs = direction_align_counter[aligned]

        for direction, count in sorted(
            dirs.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            print(f"  {direction:<10} {count}")

    #
    # PROBABILITY DISTRIBUTION
    #
    print("\n[PROBABILITY DISTRIBUTION]")

    print(
        f"{'bucket':<10}"
        f"{'true':>8}"
        f"{'false':>8}"
        f"{'null':>8}"
    )

    bucket_order = [
        "<40%",
        "40-50%",
        "50-60%",
        "60-70%",
        "70-80%",
        ">=80%",
        "unknown",
    ]

    for bucket in bucket_order:

        c = prob_dist[bucket]

        print(
            f"{bucket:<10}"
            f"{c['true']:>8}"
            f"{c['false']:>8}"
            f"{c['null']:>8}"
        )

    #
    # AVERAGE PROBABILITY
    #
    print("\n[AVERAGE PROBABILITY]")

    if prob_true:
        print(
            f"aligned=true   count={len(prob_true):>4} "
            f"avg={mean(prob_true):.4f}"
        )

    if prob_false:
        print(
            f"aligned=false  count={len(prob_false):>4} "
            f"avg={mean(prob_false):.4f}"
        )

    #
    # TOP CONTRARIAN
    #
    ranking_contra = []

    for inst, c in inst_counter.items():

        t = c["true"]
        f = c["false"]

        valid = t + f

        if valid < 5:
            continue

        ratio = f / valid

        ranking_contra.append(
            (
                ratio,
                inst,
                t,
                f,
                valid,
            )
        )

    ranking_contra.sort(reverse=True)

    print("\n[TOP CONTRARIAN INSTRUMENTS]")

    print(
        f"{'instrument':<12}"
        f"{'aligned':>10}"
        f"{'contra':>10}"
        f"{'ratio':>10}"
    )

    for ratio, inst, t, f, valid in ranking_contra[:10]:

        print(
            f"{inst:<12}"
            f"{t:>10}"
            f"{f:>10}"
            f"{ratio:>9.1%}"
        )

    #
    # TOP ALIGNED
    #
    ranking_aligned = []

    for inst, c in inst_counter.items():

        t = c["true"]
        f = c["false"]

        valid = t + f

        if valid < 5:
            continue

        ratio = t / valid

        ranking_aligned.append(
            (
                ratio,
                inst,
                t,
                f,
                valid,
            )
        )

    ranking_aligned.sort(reverse=True)

    print("\n[TOP ALIGNED INSTRUMENTS]")

    print(
        f"{'instrument':<12}"
        f"{'aligned':>10}"
        f"{'contra':>10}"
        f"{'ratio':>10}"
    )

    for ratio, inst, t, f, valid in ranking_aligned[:10]:

        print(
            f"{inst:<12}"
            f"{t:>10}"
            f"{f:>10}"
            f"{ratio:>9.1%}"
        )

    print()


if __name__ == "__main__":
    main()