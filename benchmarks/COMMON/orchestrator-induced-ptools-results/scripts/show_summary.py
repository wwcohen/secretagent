#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas"]
# ///
"""Print the induced-seed orchestrator test-set summary table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONDITION = "orch_induced_seed_ptools"
ROWS = [
    ("musr_murder", "musr"),
    ("musr_object", "musr"),
    ("musr_team", "musr"),
    ("natplan_meeting", "natural_plan"),
    ("natplan_trip", "natural_plan"),
    ("rulearena_nba", "rulearena"),
]


def find_run(bench_dir: str, row_name: str) -> Path | None:
    base = ROOT / bench_dir / "test_results_full"
    if not base.is_dir():
        return None
    runs = [
        p for p in base.iterdir()
        if p.is_dir()
        and (p / "results.csv").exists()
        and row_name in p.name
        and CONDITION in p.name
    ]
    return sorted(runs, key=lambda p: p.name)[-1] if runs else None


def cell_stats(csv: Path) -> tuple[int, float, float]:
    df = pd.read_csv(csv)
    n = len(df)
    acc = df["correct"].mean() * 100.0 if "correct" in df else float("nan")
    cost = df["cost"].sum() if "cost" in df else 0.0
    return n, acc, cost


def fmt_cost(c: float) -> str:
    if pd.isna(c):
        return "-"
    if c == 0.0:
        return "$0.0000"
    return f"${c:.4f}"


def main() -> None:
    rows = []
    for label, bench_dir in ROWS:
        run = find_run(bench_dir, label)
        if run is None:
            rows.append((label, 0, float("nan"), float("nan")))
            continue
        rows.append((label, *cell_stats(run / "results.csv")))

    print()
    print("=" * 76)
    print("  Orchestrator-generated workflow + induced seed ptools")
    print("=" * 76)
    print(f"  {'Benchmark':<32}  {'n':>5}  {'Accuracy':>9}  {'Cost':>12}")
    print("  " + "-" * 64)
    for label, n, acc, cost in rows:
        acc_s = f"{acc:.1f}%" if not pd.isna(acc) else "-"
        print(f"  {label:<32}  {n:>5}  {acc_s:>9}  {fmt_cost(cost):>12}")
    print()
    print("  All rows are held-out test-set runs with together_ai/deepseek-ai/DeepSeek-V3.1.")
    print()


if __name__ == "__main__":
    main()
