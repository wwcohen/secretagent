#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas"]
# ///
"""Print accuracy + cost tables for both orchestrator test conditions.

Two tables:
  - Handcrafted workflow + orchestrator-improved ptools
  - Orchestrator-generated workflow + orchestrator-improved ptools

The report reads the canonical codedistill-style tree:
`<bench>/test_results_full/<TS>.<subbench>_test_full_<condition>/`.

The old `existing_workflow/` and `seed_from_ptools/` trees remain for
provenance only. NBA uses the unpatched `without_rulebook` seed run; the
manual rulebook fix is intentionally excluded.

medcalc is always reported as formulas and rules; the overall mix is not
used for headline tables.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]  # orchestrator-results/

CONDITIONS = {
    "orch_existing_workflow": "Handcrafted workflow + orchestrator-improved ptools",
    "orch_seed_from_ptools": "Orchestrator-generated workflow + orchestrator-improved ptools",
}

ROWS = [
    ("medcalc/formulas", "medcalc", "medcalc_formulas"),
    ("medcalc/rules", "medcalc", "medcalc_rules"),
    ("musr_murder", "musr", "musr_murder"),
    ("musr_object", "musr", "musr_object"),
    ("musr_team", "musr", "musr_team"),
    ("natplan_calendar", "natural_plan", "natplan_calendar"),
    ("natplan_meeting", "natural_plan", "natplan_meeting"),
    ("natplan_trip", "natural_plan", "natplan_trip"),
    ("rulearena_nba", "rulearena", "rulearena_nba"),
]


def cell_stats(csv: Path) -> tuple[int, float, float]:
    """Return (n_rows, accuracy_pct, total_cost). NaN cost stays NaN."""
    if not csv.exists():
        return (0, float("nan"), float("nan"))
    df = pd.read_csv(csv)
    n = len(df)
    acc = df["correct"].mean() * 100.0 if "correct" in df else float("nan")
    cost = df["cost"].sum() if "cost" in df else float("nan")
    return n, acc, cost


def find_run(bench_dir: str, row_name: str, condition: str) -> Path | None:
    """Locate the latest canonical test run for a row/condition."""
    base = ROOT / bench_dir / "test_results_full"
    if not base.is_dir():
        return None
    runs = [
        p for p in base.iterdir()
        if p.is_dir()
        and (p / "results.csv").exists()
        and row_name in p.name
        and condition in p.name
    ]
    if not runs:
        return None
    return sorted(runs, key=lambda p: p.name)[-1]


def row(label: str, bench_dir: str, row_name: str, condition: str) -> tuple[str, int, float, float]:
    run = find_run(bench_dir, row_name, condition)
    if run is None:
        return (label, 0, float("nan"), float("nan"))
    n, acc, cost = cell_stats(run / "results.csv")
    return (label, n, acc, cost)


def fmt_cost(c: float) -> str:
    if pd.isna(c):
        return "—"
    if c == 0.0:
        return "$0.00 (no LLM)"
    return f"${c:.2f}"


def render_table(title: str, rows: list[tuple[str, int, float, float]]) -> str:
    out = []
    bar = "=" * 76
    out.append(bar)
    out.append(f"  {title}")
    out.append(bar)
    out.append(f"  {'Benchmark':<48}  {'n':>5}  {'Accuracy':>9}  {'Cost':>14}")
    out.append("  " + "-" * 84)
    for label, n, acc, cost in rows:
        acc_s = f"{acc:.1f}%" if not pd.isna(acc) else "—"
        out.append(f"  {label:<48}  {n:>5}  {acc_s:>9}  {fmt_cost(cost):>14}")
    return "\n".join(out)


def render_delta_table(title: str, rows: list[tuple[str, tuple[int, float, float], tuple[int, float, float]]]) -> str:
    """rows: (label, (n_e, acc_e, cost_e), (n_s, acc_s, cost_s))"""
    out = []
    bar = "=" * 90
    out.append(bar)
    out.append(f"  {title}")
    out.append(bar)
    out.append(f"  {'Benchmark':<48}  {'existing':>8}  {'seed':>8}  {'Δacc':>8}  {'Δcost':>9}")
    out.append("  " + "-" * 88)
    for label, (n_e, acc_e, cost_e), (n_s, acc_s, cost_s) in rows:
        if pd.isna(acc_e) or pd.isna(acc_s):
            d_acc = "—"
        else:
            dval = acc_s - acc_e
            d_acc = f"{dval:+.1f}pp"
        if pd.isna(cost_e) or pd.isna(cost_s):
            d_cost = "—"
        else:
            dc = cost_s - cost_e
            d_cost = f"{dc:+.2f}"
        acc_e_s = f"{acc_e:.1f}%" if not pd.isna(acc_e) else "—"
        acc_s_s = f"{acc_s:.1f}%" if not pd.isna(acc_s) else "—"
        out.append(f"  {label:<48}  {acc_e_s:>8}  {acc_s_s:>8}  {d_acc:>8}  ${d_cost:>8}")
    return "\n".join(out)


def main() -> None:
    existing = [
        row(label, bench_dir, row_name, "orch_existing_workflow")
        for label, bench_dir, row_name in ROWS
    ]
    seed = [
        row(label, bench_dir, row_name, "orch_seed_from_ptools")
        for label, bench_dir, row_name in ROWS
    ]
    # Build deltas: pair each existing-workflow row with the matching seed row.
    def _stat(bench_dir: str, row_name: str, condition: str) -> tuple[int, float, float]:
        run = find_run(bench_dir, row_name, condition)
        return cell_stats(run / "results.csv") if run else (0, float("nan"), float("nan"))

    delta_rows = [
        (
            label,
            _stat(bench_dir, row_name, "orch_existing_workflow"),
            _stat(bench_dir, row_name, "orch_seed_from_ptools"),
        )
        for label, bench_dir, row_name in ROWS
    ]

    print()
    print(render_table(CONDITIONS["orch_existing_workflow"], existing))
    print()
    print(render_table(CONDITIONS["orch_seed_from_ptools"], seed))
    print()
    print(render_delta_table("Delta (orch_seed_from_ptools - orch_existing_workflow)", delta_rows))
    print()
    print(_FOOTNOTES)
    print()


_FOOTNOTES = """  Footnotes
  ---------
  All rows are held-out test-set runs with together_ai/deepseek-ai/DeepSeek-V3.1.

  medcalc is split into formulas and rules. The overall mixed run is intentionally
  omitted because the categories have different difficulty profiles.

  rulearena_nba uses the default seed_from_ptools NBA run, which does not include
  the manual rulebook fix. The with_rulebook/fix artifacts remain under the
  preserved legacy layout for provenance, but are excluded from these tables."""


if __name__ == "__main__":
    main()
