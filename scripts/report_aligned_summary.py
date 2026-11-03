#!/usr/bin/env python3
import json
from collections import Counter, defaultdict
from pathlib import Path

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


def main():
    rows = load_rows(LIFECYCLE_FILE)

    print("=" * 70)
    print("ALIGNED SUMMARY REPORT")
    print("=" * 70)

    aligned_counter = Counter()
    stage_counter = defaultdict(Counter)
    inst_counter = defaultdict(Counter)

    for r in rows:
        aligned = r.get("aligned")

        if aligned is True:
            key = "true"
        elif aligned is False:
            key = "false"
        else:
            key = "null"

        aligned_counter[key] += 1

        stage = r.get("trend_stage", "UNKNOWN")
        stage_counter[stage][key] += 1

        inst = r.get("instrument", "UNKNOWN")
        inst_counter[inst][key] += 1

    total = sum(aligned_counter.values())

    print("\n[ALIGNMENT]")
    for k in ("true", "false", "null"):
        n = aligned_counter[k]
        pct = n * 100 / total if total else 0
        print(f"{k:>5}: {n:>6} ({pct:6.2f}%)")

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

    print("\n[TOP CONTRARIAN INSTRUMENTS]")

    ranking = []

    for inst, c in inst_counter.items():
        t = c["true"]
        f = c["false"]

        total_valid = t + f

        if total_valid < 5:
            continue

        contrarian_ratio = f / total_valid

        ranking.append(
            (
                contrarian_ratio,
                inst,
                t,
                f,
                total_valid,
            )
        )

    ranking.sort(reverse=True)

    print(
        f"{'instrument':<12}"
        f"{'aligned':>10}"
        f"{'contra':>10}"
        f"{'ratio':>10}"
    )

    for ratio, inst, t, f, n in ranking[:10]:
        print(
            f"{inst:<12}"
            f"{t:>10}"
            f"{f:>10}"
            f"{ratio:>9.1%}"
        )

    print()


if __name__ == "__main__":
    main()