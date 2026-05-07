#!/usr/bin/env python3
"""Summarize induced seed-from-ptools learner and test results."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[2]

ROWS = [
    ("musr_murder", "musr", "ptools_murder_induced_seed", "murder_mysteries_test", 70, 30, 100, "musr_murder_induced_seed_ptools_deepseek_v3_1"),
    ("musr_object", "musr", "ptools_object_induced_seed", "object_placements_test", 74, 32, 106, "musr_object_induced_seed_ptools_deepseek_v3_1"),
    ("musr_team", "musr", "ptools_team_induced_seed", "team_allocation_test", 70, 30, 100, "musr_team_induced_seed_ptools_deepseek_v3_1"),
    ("natplan_meeting", "natural_plan", "ptools_meeting_induced_seed", "meeting", 70, 30, 100, "natplan_meeting_induced_seed_ptools_deepseek_v3_1"),
    ("natplan_trip", "natural_plan", "ptools_trip_induced_seed", "trip", 70, 30, 100, "natplan_trip_induced_seed_ptools_deepseek_v3_1"),
    ("rulearena_nba", "rulearena", "ptools_nba_induced_seed", "valid", 29, 13, 46, "rulearena_nba_induced_seed_ptools_deepseek_v3_1"),
]


def find_run(bench_dir: Path, ptools_module: str, split: str, n_train: int, n_eval: int) -> Path | None:
    matches = []
    for meta_path in (bench_dir / "results/orchestration_learner").glob("*.orch_learner/run_metadata.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        if (
            meta.get("ptools_module") == ptools_module
            and meta.get("seed_orchestrate") is True
            and meta.get("scratch_evolved") is True
            and meta.get("train_split") == split
            and meta.get("eval_split") == split
            and meta.get("n_train") == n_train
            and meta.get("n_eval") == n_eval
            and meta.get("max_iterations") == 5
        ):
            matches.append(meta_path.parent)
    return sorted(matches)[-1] if matches else None


def latest_csv(bench_dir: Path, tag: str) -> Path | None:
    matches = sorted((bench_dir / "test_results_full").glob(f"*.{tag}/results.csv"))
    return matches[-1] if matches else None


def numeric_cell(value: str | None) -> float:
    if value is None:
        return 0.0
    value = value.strip()
    if not value:
        return 0.0
    if value.lower() == "true":
        return 1.0
    if value.lower() == "false":
        return 0.0
    return float(value)


def result_stats(csv_path: Path) -> tuple[int, float, float]:
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    n = len(rows)
    correct_vals = [numeric_cell(r.get("correct")) for r in rows]
    cost_vals = [numeric_cell(r.get("cost")) for r in rows]
    return n, sum(correct_vals) / n if n else 0.0, sum(cost_vals)


def main() -> None:
    print("| benchmark | learner dir | final workflow | test rows | accuracy | cost | test dir |")
    print("|---|---|---|---:|---:|---:|---|")
    for label, bench_rel, ptools_module, split, n_train, n_eval, expected, tag in ROWS:
        bench_dir = REPO / "benchmarks" / bench_rel
        run = find_run(bench_dir, ptools_module, split, n_train, n_eval)
        workflow = ""
        if run:
            impl = yaml.safe_load((run / "implementation.yaml").read_text())
            entry = next(iter(impl))
            workflow = impl[entry]["fn"]
        csv_path = latest_csv(bench_dir, tag)
        if csv_path:
            n, acc, cost = result_stats(csv_path)
            row_status = str(n) if n == expected else f"{n} (expected {expected})"
            test_dir = csv_path.parent
            print(
                f"| {label} | {run or 'MISSING'} | {workflow or 'MISSING'} | "
                f"{row_status} | {acc:.1%} | ${cost:.4f} | {test_dir} |"
            )
        else:
            print(
                f"| {label} | {run or 'MISSING'} | {workflow or 'MISSING'} | "
                f"MISSING | MISSING | MISSING | MISSING |"
            )


if __name__ == "__main__":
    main()
