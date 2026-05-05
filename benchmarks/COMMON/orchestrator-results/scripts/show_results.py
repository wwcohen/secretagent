#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas",
#   "pyyaml",
# ]
# ///
"""Summarise test-set re-evaluations under benchmarks/COMMON/orchestrator-results/.

Looks for `<class>/<bench>/<TS>.<expt_tag>/results.csv`, prints a markdown
matrix (rows=bench, cols=class) and a long-format dump.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]  # orchestrator-results/
CLASSES = ["existing_workflow", "seed_from_ptools"]
BENCHES = [
    "medcalc",
    "musr_murder", "musr_object", "musr_team",
    "natplan_calendar", "natplan_meeting", "natplan_trip",
    "rulearena_nba",
]


def _latest_run(bench_dir: Path, expt_tag: str | None) -> Path | None:
    if not bench_dir.is_dir():
        return None
    # Prefer results/ subtree if it exists (post-reorganization layout).
    # (older runs may still have final/ — fall back to that for backwards compat.)
    if (bench_dir / "results").is_dir():
        search_root = bench_dir / "results"
    elif (bench_dir / "final").is_dir():
        search_root = bench_dir / "final"
    else:
        search_root = bench_dir
    # medcalc has variant subdirs (learned_from_*_traces/) under results/.
    # Default the bench-level summary row to learned_from_all_traces/overall/.
    if (search_root / "learned_from_all_traces").is_dir():
        search_root = search_root / "learned_from_all_traces" / "overall"
    elif (search_root / "combined").is_dir():
        search_root = search_root / "combined"
    # rulearena_nba seed has variants under results/{without_rulebook,with_rulebook}.
    # Default the summary row to with_rulebook (the cleaner number).
    elif (search_root / "with_rulebook").is_dir():
        search_root = search_root / "with_rulebook"
    candidates = [p for p in search_root.iterdir()
                  if p.is_dir() and (p / "results.csv").exists()]
    if expt_tag:
        candidates = [p for p in candidates
                      if p.name.split(".", 2)[-1] == expt_tag]
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


def collect(expt_tag: str | None) -> pd.DataFrame:
    rows = []
    for bench in BENCHES:
        for cls in CLASSES:
            run_dir = _latest_run(ROOT / cls / bench, expt_tag)
            if run_dir is None:
                rows.append({"bench": bench, "class": cls, "run_dir": None,
                             "n": 0, "accuracy": float("nan"),
                             "total_cost": float("nan"),
                             "avg_cost": float("nan"),
                             "avg_input_tokens": float("nan"),
                             "avg_output_tokens": float("nan"),
                             "model": None, "fn": None})
                continue
            row = {"bench": bench, "class": cls, **_summarize(run_dir)}
            rows.append(row)
    return pd.DataFrame(rows)


def render_markdown(df: pd.DataFrame) -> str:
    lines = ["| Bench | existing_workflow | seed_from_ptools |",
             "|---|---|---|"]
    for bench in BENCHES:
        cells = [bench]
        for cls in CLASSES:
            r = df[(df["bench"] == bench) & (df["class"] == cls)]
            if r.empty or r.iloc[0]["run_dir"] is None:
                cells.append("—")
                continue
            r = r.iloc[0]
            cells.append(
                f"{r['accuracy']:.1f}% (n={int(r['n'])}) / ${r['total_cost']:.2f}"
            )
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_long(df: pd.DataFrame) -> str:
    cols = ["bench", "class", "n", "accuracy", "total_cost", "avg_cost",
            "avg_input_tokens", "avg_output_tokens", "model", "fn", "run_dir"]
    return df[cols].to_csv(index=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--expt-tag", default="test_deepseek_v3_1",
                    help="Filter to runs whose dir tag equals this. "
                         "Use empty string '' to disable.")
    ap.add_argument("--csv", type=Path, default=None,
                    help="Write long-format CSV to this path.")
    ap.add_argument("--md", type=Path, default=None,
                    help="Write markdown table to this path.")
    args = ap.parse_args()

    expt_tag = args.expt_tag or None
    df = collect(expt_tag)

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
