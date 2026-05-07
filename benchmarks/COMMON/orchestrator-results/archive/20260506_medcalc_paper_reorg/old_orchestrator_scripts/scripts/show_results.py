#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas",
#   "pyyaml",
# ]
# ///
"""Summarise orchestrator test-set re-evaluations.

Canonical results use the same layout as the COMMON codedistill exports:

    <bench>/test_results_full/<TS>.<subbench>_test_full_<condition>/results.csv

The older `existing_workflow/<bench>/...` and `seed_from_ptools/<bench>/...`
trees remain in place for provenance, but this report reads the canonical tree.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]  # orchestrator-results/
CONDITIONS = ["orch_existing_workflow", "orch_seed_from_ptools"]
ROWS = [
    ("medcalc_formulas", "medcalc"),
    ("medcalc_rules", "medcalc"),
    ("musr_murder", "musr"),
    ("musr_object", "musr"),
    ("musr_team", "musr"),
    ("natplan_calendar", "natural_plan"),
    ("natplan_meeting", "natural_plan"),
    ("natplan_trip", "natural_plan"),
    ("rulearena_nba", "rulearena"),
]


def _latest_run(bench_root: Path, row_name: str, condition: str) -> Path | None:
    search_root = bench_root / "test_results_full"
    if not search_root.is_dir():
        return None
    candidates = [
        p for p in search_root.iterdir()
        if p.is_dir()
        and (p / "results.csv").exists()
        and row_name in p.name
        and condition in p.name
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


def _summarize(run_dir: Path) -> dict:
    df = pd.read_csv(run_dir / "results.csv")
    n = len(df)
    acc = float(df["correct"].mean()) * 100.0 if n and "correct" in df else float("nan")
    total_cost = float(df["cost"].sum()) if "cost" in df else float("nan")
    avg_cost = float(df["cost"].mean()) if "cost" in df and n else float("nan")
    in_tok = float(df["input_tokens"].mean()) if "input_tokens" in df and n else float("nan")
    out_tok = float(df["output_tokens"].mean()) if "output_tokens" in df and n else float("nan")
    cfg = {}
    cfg_path = run_dir / "config.yaml"
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
    return {
        "run_dir": str(run_dir.relative_to(ROOT)),
        "n": n,
        "accuracy": acc,
        "total_cost": total_cost,
        "avg_cost": avg_cost,
        "avg_input_tokens": in_tok,
        "avg_output_tokens": out_tok,
        "model": (cfg.get("llm") or {}).get("model"),
        "fn": ((cfg.get("ptools") or {}).get(
                ((cfg.get("evaluate") or {}).get("entry_point") or "")) or {}).get("fn"),
    }


def collect() -> pd.DataFrame:
    rows = []
    for row_name, bench_dir in ROWS:
        for condition in CONDITIONS:
            run_dir = _latest_run(ROOT / bench_dir, row_name, condition)
            if run_dir is None:
                rows.append({"bench": row_name, "condition": condition, "run_dir": None,
                             "n": 0, "accuracy": float("nan"),
                             "total_cost": float("nan"),
                             "avg_cost": float("nan"),
                             "avg_input_tokens": float("nan"),
                             "avg_output_tokens": float("nan"),
                             "model": None, "fn": None})
                continue
            row = {"bench": row_name, "condition": condition, **_summarize(run_dir)}
            rows.append(row)
    return pd.DataFrame(rows)


def render_markdown(df: pd.DataFrame) -> str:
    lines = ["| Bench | orch_existing_workflow | orch_seed_from_ptools |",
             "|---|---|---|"]
    for row_name, _bench_dir in ROWS:
        cells = [row_name]
        for condition in CONDITIONS:
            r = df[(df["bench"] == row_name) & (df["condition"] == condition)]
            if r.empty or r.iloc[0]["run_dir"] is None:
                cells.append("—")
                continue
            r = r.iloc[0]
            cost = "—" if pd.isna(r["total_cost"]) else f"${r['total_cost']:.2f}"
            cells.append(
                f"{r['accuracy']:.1f}% (n={int(r['n'])}) / {cost}"
            )
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_long(df: pd.DataFrame) -> str:
    cols = ["bench", "condition", "n", "accuracy", "total_cost", "avg_cost",
            "avg_input_tokens", "avg_output_tokens", "model", "fn", "run_dir"]
    return df[cols].to_csv(index=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=None,
                    help="Write long-format CSV to this path.")
    ap.add_argument("--md", type=Path, default=None,
                    help="Write markdown table to this path.")
    args = ap.parse_args()

    df = collect()

    md = render_markdown(df)
    long = render_long(df)

    if args.md:
        args.md.write_text(md + "\n")
    if args.csv:
        args.csv.write_text(long)

    print("# Markdown summary")
    print(md)
    print()
    print("# Long-format dump")
    print(long)


if __name__ == "__main__":
    main()
