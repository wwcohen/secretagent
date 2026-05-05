"""Run a test-split evaluation on the Pareto-optimal configs from an NSGA-II sweep.

Methodology: optimizer scored on valid; this script picks the configs that survived
the search and re-runs each one on the held-out test split. Produces standard
savefile result dirs (same shape as cli.expt output) plus a flat test_pass_summary.csv
that pairs valid_correct / valid_cost (from the optimizer) with test_correct /
test_cost (from this script).

Usage:
    uv run python benchmarks/COMMON/optimize-results/test_pass.py <bench> [--dry-run]

    bench is one of: sports, medcalc, tabmwp, nba, musr_murder, musr_team,
                     natplan_meeting, natplan_trip

    finqa is skipped: FinQA's leaderboard test set is private; the public release
    only includes dev (which the optimizer already used as 'valid').
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class BenchSpec:
    name: str                       # short name used as snapshot dir
    cwd: Path                       # benchmark working directory
    space_yaml: Path                # nsga2.yaml with methods: dict
    summary_csv: Path               # nsga2_summary.csv with frontier column
    snapshot_dir: Path              # benchmarks/COMMON/optimize-results/<name>/
    test_split: str                 # split=<this> for test-pass eval
    extra_dotlist: list[str]        # additional dotlist overrides (e.g. dataset.n)


BENCHES: dict[str, BenchSpec] = {
    "sports": BenchSpec(
        name="sports_understanding",
        cwd=REPO_ROOT / "benchmarks/bbh/sports_understanding",
        space_yaml=REPO_ROOT / "benchmarks/bbh/sports_understanding/nsga2.yaml",
        summary_csv=REPO_ROOT / "benchmarks/COMMON/optimize-results/sports_understanding/nsga2_summary.csv",
        snapshot_dir=REPO_ROOT / "benchmarks/COMMON/optimize-results/sports_understanding",
        test_split="test",
        extra_dotlist=["dataset.n=100"],
    ),
    "medcalc": BenchSpec(
        name="medcalc",
        cwd=REPO_ROOT / "benchmarks/medcalc",
        space_yaml=REPO_ROOT / "benchmarks/medcalc/nsga2.yaml",
        summary_csv=REPO_ROOT / "benchmarks/medcalc/results/nsga2_summary.csv",
        snapshot_dir=REPO_ROOT / "benchmarks/COMMON/optimize-results/medcalc",
        test_split="test",
        extra_dotlist=["dataset.stratified=true", "dataset.shuffle_seed=42", "dataset.n=300"],
    ),
    "tabmwp": BenchSpec(
        name="tabmwp",
        cwd=REPO_ROOT / "benchmarks/tabmwp",
        space_yaml=REPO_ROOT / "benchmarks/tabmwp/nsga2.yaml",
        summary_csv=REPO_ROOT / "benchmarks/COMMON/optimize-results/tabmwp/nsga2_summary.csv",
        snapshot_dir=REPO_ROOT / "benchmarks/COMMON/optimize-results/tabmwp",
        test_split="test1k",
        extra_dotlist=["dataset.n=500"],
    ),
    "nba": BenchSpec(
        name="rulearena_nba",
        cwd=REPO_ROOT / "benchmarks/rulearena/nba",
        space_yaml=REPO_ROOT / "benchmarks/rulearena/nsga2_nba.yaml",
        summary_csv=REPO_ROOT / "benchmarks/COMMON/optimize-results/rulearena_nba/nsga2_summary.csv",
        snapshot_dir=REPO_ROOT / "benchmarks/COMMON/optimize-results/rulearena_nba",
        test_split="test",
        extra_dotlist=["dataset.n=50"],
    ),
    "musr_murder": BenchSpec(
        name="musr_murder",
        cwd=REPO_ROOT / "benchmarks/musr",
        space_yaml=REPO_ROOT / "benchmarks/musr/nsga2_murder.yaml",
        summary_csv=REPO_ROOT / "benchmarks/COMMON/optimize-results/musr_murder/nsga2_summary.csv",
        snapshot_dir=REPO_ROOT / "benchmarks/COMMON/optimize-results/musr_murder",
        test_split="murder_mysteries_test",
        extra_dotlist=["dataset.n=50"],
    ),
    "musr_team": BenchSpec(
        name="musr_team",
        cwd=REPO_ROOT / "benchmarks/musr",
        space_yaml=REPO_ROOT / "benchmarks/musr/nsga2_team.yaml",
        summary_csv=REPO_ROOT / "benchmarks/COMMON/optimize-results/musr_team/nsga2_summary.csv",
        snapshot_dir=REPO_ROOT / "benchmarks/COMMON/optimize-results/musr_team",
        test_split="team_allocation_test",
        extra_dotlist=["dataset.n=50"],
    ),
    "natplan_meeting": BenchSpec(
        name="natplan_meeting",
        cwd=REPO_ROOT / "benchmarks/natural_plan",
        space_yaml=REPO_ROOT / "benchmarks/natural_plan/nsga2_meeting.yaml",
        summary_csv=REPO_ROOT / "benchmarks/COMMON/optimize-results/natplan_meeting/nsga2_summary.csv",
        snapshot_dir=REPO_ROOT / "benchmarks/COMMON/optimize-results/natplan_meeting",
        test_split="meeting",
        extra_dotlist=["dataset.partition=test", "dataset.n=50"],
    ),
    "natplan_trip": BenchSpec(
        name="natplan_trip",
        cwd=REPO_ROOT / "benchmarks/natural_plan",
        space_yaml=REPO_ROOT / "benchmarks/natural_plan/nsga2_trip.yaml",
        summary_csv=REPO_ROOT / "benchmarks/COMMON/optimize-results/natplan_trip/nsga2_summary.csv",
        snapshot_dir=REPO_ROOT / "benchmarks/COMMON/optimize-results/natplan_trip",
        test_split="trip",
        extra_dotlist=["dataset.partition=test", "dataset.n=50"],
    ),
}


# Map short model name in summary CSV (e.g. 'gemini-2.5-flash')
# to the full model id used as llm.model dotlist override.
MODEL_FULL = {
    "DeepSeek-V3": "together_ai/deepseek-ai/DeepSeek-V3",
    "DeepSeek-V3.1": "together_ai/deepseek-ai/DeepSeek-V3.1",
    "gpt-oss-20b": "together_ai/openai/gpt-oss-20b",
    "gpt-oss-120b": "together_ai/openai/gpt-oss-120b",
    "gemini-2.5-flash": "gemini/gemini-2.5-flash",
    "gemini-2.5-flash-lite": "gemini/gemini-2.5-flash-lite",
}


def slugify(model_short: str) -> str:
    return model_short.replace("/", "_").replace(".", "-")


def load_space(space_yaml: Path) -> dict:
    with open(space_yaml, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_command(space: dict, bench: BenchSpec, method: str, model_short: str) -> list[str]:
    method_dotlist = list(space["methods"][method])
    model_full = MODEL_FULL[model_short]
    expt_name = f"test_pass_{method}_{slugify(model_short)}"

    if "command" in space:
        # Benchmarks with a custom command (medcalc, tabmwp, musr).
        base = shlex.split(space["command"])
    else:
        # Use cli.expt run with interface (+ optional evaluator) from yaml.
        base = ["uv", "run", "python", "-m", "secretagent.cli.expt", "run",
                "--interface", space["interface"]]
        if "evaluator" in space:
            base += ["--evaluator", space["evaluator"]]

    return [
        *base,
        f"llm.model={model_full}",
        *method_dotlist,
        f"dataset.split={bench.test_split}",
        *bench.extra_dotlist,
        f"evaluate.expt_name={expt_name}",
    ]


def run_one(cmd: list[str], cwd: Path, dry_run: bool) -> int:
    print(f"\n>>> cd {cwd}")
    print(f">>> {' '.join(shlex.quote(c) for c in cmd)}")
    if dry_run:
        return 0
    return subprocess.call(cmd, cwd=str(cwd))


def find_result_dir(cwd: Path, expt_name: str) -> Path | None:
    """Return the most recent results/<TS>.<expt_name>/ dir."""
    results_dir = cwd / "results"
    if not results_dir.exists():
        return None
    matches = sorted(results_dir.glob(f"*.{expt_name}"))
    return matches[-1] if matches else None


def collect_summary(bench: BenchSpec, frontier: pd.DataFrame) -> pd.DataFrame:
    """Pair each Pareto row's valid numbers with test numbers from results.csv."""
    rows = []
    for _, r in frontier.iterrows():
        method, model_short = r["method"], r["model"]
        expt_name = f"test_pass_{method}_{slugify(model_short)}"
        rdir = find_result_dir(bench.cwd, expt_name)
        if rdir is None:
            test_correct = test_cost = float("nan")
            n_test = 0
        else:
            df = pd.read_csv(rdir / "results.csv")
            test_correct = df["correct"].mean() if "correct" in df.columns else float("nan")
            test_cost = df["cost"].sum() if "cost" in df.columns else float("nan")
            n_test = len(df)
        rows.append({
            "method": method,
            "model": model_short,
            "valid_correct": r["correct"],
            "valid_cost": r["cost"],
            "test_correct": test_correct,
            "test_cost": test_cost,
            "n_test": n_test,
            "expt_name": expt_name,
        })
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bench", choices=list(BENCHES.keys()))
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands; don't execute")
    parser.add_argument("--only-method", help="Run only this method (smoke test)")
    parser.add_argument("--only-model", help="Run only this model (smoke test)")
    parser.add_argument("--summary-only", action="store_true",
                        help="Skip running; just rebuild test_pass_summary.csv from existing dirs")
    args = parser.parse_args()

    bench = BENCHES[args.bench]
    space = load_space(bench.space_yaml)

    df = pd.read_csv(bench.summary_csv)
    frontier = df[(df["frontier"] == True) & (df["valid"] == True)].copy()
    # Dedupe (method, model) — same config can appear multiple times via cache hits
    frontier = frontier.drop_duplicates(subset=["method", "model"]).sort_values(
        "correct", ascending=False
    )

    if args.only_method:
        frontier = frontier[frontier["method"] == args.only_method]
    if args.only_model:
        frontier = frontier[frontier["model"] == args.only_model]

    print(f"=== {bench.name}: {len(frontier)} Pareto-optimal config(s); test split={bench.test_split} ===")
    for _, r in frontier.iterrows():
        print(f"  {r['method']:<22} / {r['model']:<25} valid={r['correct']:.1%} ${r['cost']:.5f}")

    rc = 0
    if not args.summary_only:
        for _, r in frontier.iterrows():
            cmd = build_command(space, bench, r["method"], r["model"])
            rc = run_one(cmd, bench.cwd, args.dry_run)
            if rc != 0:
                print(f"!!! command failed (rc={rc}); continuing with the rest")

    if args.summary_only:
        # Rebuild summary using ALL frontier configs (ignore --only-* filters
        # so the saved CSV is complete).
        df_full = pd.read_csv(bench.summary_csv)
        full_frontier = df_full[(df_full["frontier"] == True) & (df_full["valid"] == True)].copy()
        full_frontier = full_frontier.drop_duplicates(
            subset=["method", "model"]
        ).sort_values("correct", ascending=False)
        summary = collect_summary(bench, full_frontier)
        out_path = bench.snapshot_dir / "test_pass_summary.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(out_path, index=False)
        print(f"\nWrote {out_path}")
        print(summary.to_string(index=False))
        return 0

    if not args.dry_run:
        summary = collect_summary(bench, frontier)
        out_path = bench.snapshot_dir / "test_pass_summary.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(out_path, index=False)
        print(f"\nWrote {out_path}")
        print(summary.to_string(index=False))

    return rc


if __name__ == "__main__":
    sys.exit(main())
