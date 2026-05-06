#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas",
#   "pyyaml",
# ]
# ///
"""Summarise induced-seed orchestrator test-set re-evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

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


def _latest_run(bench_root: Path, row_name: str) -> Path | None:
    search_root = bench_root / "test_results_full"
    if not search_root.is_dir():
        return None
    candidates = [
        p for p in search_root.iterdir()
        if p.is_dir()
        and (p / "results.csv").exists()
        and row_name in p.name
        and CONDITION in p.name
    ]
    return sorted(candidates, key=lambda p: p.name)[-1] if candidates else None


def _summarize(run_dir: Path) -> dict:
    df = pd.read_csv(run_dir / "results.csv")
    n = len(df)
    acc = float(df["correct"].mean()) * 100.0 if n and "correct" in df else float("nan")
    total_cost = float(df["cost"].sum()) if "cost" in df else 0.0
    avg_cost = float(df["cost"].mean()) if "cost" in df and n else 0.0
    in_tok = float(df["input_tokens"].mean()) if "input_tokens" in df and n else 0.0
    out_tok = float(df["output_tokens"].mean()) if "output_tokens" in df and n else 0.0
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
        run_dir = _latest_run(ROOT / bench_dir, row_name)
        if run_dir is None:
            rows.append({"bench": row_name, "condition": CONDITION, "run_dir": None,
                         "n": 0, "accuracy": float("nan"),
                         "total_cost": float("nan"), "avg_cost": float("nan"),
                         "avg_input_tokens": float("nan"),
                         "avg_output_tokens": float("nan"), "model": None, "fn": None})
        else:
            rows.append({"bench": row_name, "condition": CONDITION, **_summarize(run_dir)})
    return pd.DataFrame(rows)


def render_markdown(df: pd.DataFrame) -> str:
    lines = [f"| Bench | {CONDITION} |", "|---|---|"]
    for row_name, _bench_dir in ROWS:
        r = df[df["bench"] == row_name]
        if r.empty or r.iloc[0]["run_dir"] is None:
            cell = "—"
        else:
            r = r.iloc[0]
            cell = f"{r['accuracy']:.1f}% (n={int(r['n'])}) / ${r['total_cost']:.4f}"
        lines.append(f"| {row_name} | {cell} |")
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
