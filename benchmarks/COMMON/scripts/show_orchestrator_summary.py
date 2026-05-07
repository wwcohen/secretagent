#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Print clear orchestrator result summaries.

Both orchestrator result trees use this one script.  Pass one or more result
roots, or pass no roots to summarize the known orchestrator result directories
under benchmarks/COMMON.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path


COMMON_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = (
    COMMON_ROOT / "orchestrator-results",
    COMMON_ROOT / "orchestrator-induced-ptools-results",
)

CONDITION_LABELS = {
    "orch_existing_workflow": "hand workflow + orchestrator-improved ptools",
    "orch_seed_from_ptools": "orchestrator-generated workflow + orchestrator-improved ptools",
    "orch_induced_seed_ptools": "orchestrator-generated workflow + induced seed ptools",
}


@dataclass(frozen=True)
class RowSpec:
    label: str
    bench_dir: str | None = None
    run_name: str | None = None
    legacy_bench: str | None = None
    direct_csv: str | None = None


ORCHESTRATOR_ROWS = (
    RowSpec("medcalc_formulas", "medcalc", "medcalc_formulas", "medcalc_formulas"),
    RowSpec("medcalc_rules", "medcalc", "medcalc_rules", "medcalc_rules"),
    RowSpec("musr_murder", "musr", "musr_murder", "musr_murder"),
    RowSpec("musr_object", "musr", "musr_object", "musr_object"),
    RowSpec("musr_team", "musr", "musr_team", "musr_team"),
    RowSpec("natplan_calendar", "natural_plan", "natplan_calendar", "natplan_calendar"),
    RowSpec("natplan_meeting", "natural_plan", "natplan_meeting", "natplan_meeting"),
    RowSpec("natplan_trip", "natural_plan", "natplan_trip", "natplan_trip"),
    RowSpec("rulearena_nba", "rulearena", "rulearena_nba", "rulearena_nba"),
)

INDUCED_ROWS = (
    RowSpec("medcalc_formulas", direct_csv="medcalc/formulas/results.csv"),
    RowSpec("medcalc_rules", direct_csv="medcalc/rules/results.csv"),
    RowSpec("musr_murder", "musr", "musr_murder"),
    RowSpec("musr_object", "musr", "musr_object"),
    RowSpec("musr_team", "musr", "musr_team"),
    RowSpec("natplan_meeting", "natural_plan", "natplan_meeting"),
    RowSpec("natplan_trip", "natural_plan", "natplan_trip"),
    RowSpec("rulearena_nba", "rulearena", "rulearena_nba"),
)

ROOT_CONFIG = {
    "orchestrator-results": (
        ("orch_existing_workflow", "orch_seed_from_ptools"),
        ORCHESTRATOR_ROWS,
    ),
    "orchestrator-induced-ptools-results": (
        ("orch_induced_seed_ptools",),
        INDUCED_ROWS,
    ),
}

LEGACY_CONDITION_DIRS = {
    "orch_existing_workflow": "existing_workflow",
    "orch_seed_from_ptools": "seed_from_ptools",
}


@dataclass(frozen=True)
class SummaryRow:
    experiment: str
    n: int
    accuracy: float
    cost: float
    csv_path: Path | None


def _parse_boolish(value: str) -> float | None:
    normalized = value.strip().lower()
    if normalized in {"true", "t", "yes", "y"}:
        return 1.0
    if normalized in {"false", "f", "no", "n"}:
        return 0.0
    if normalized == "":
        return None
    try:
        parsed = float(normalized)
    except ValueError:
        return None
    if math.isnan(parsed):
        return None
    return 1.0 if parsed != 0.0 else 0.0


def _parse_cost(value: str) -> float | None:
    if value.strip() == "":
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def summarize_csv(path: Path) -> tuple[int, float, float]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    n = len(rows)

    correct_values = [
        parsed
        for row in rows
        if (parsed := _parse_boolish(row.get("correct", ""))) is not None
    ]
    accuracy = (
        sum(correct_values) / len(correct_values) * 100.0
        if correct_values
        else math.nan
    )

    cost_values = [
        parsed
        for row in rows
        if (parsed := _parse_cost(row.get("cost", ""))) is not None
    ]
    cost = sum(cost_values)
    return n, accuracy, cost


def _latest_canonical_csv(root: Path, row: RowSpec, condition: str) -> Path | None:
    if row.bench_dir is None or row.run_name is None:
        return None
    search_root = root / row.bench_dir / "test_results_full"
    if not search_root.is_dir():
        return None
    candidates = [
        p / "results.csv"
        for p in search_root.iterdir()
        if p.is_dir()
        and (p / "results.csv").exists()
        and row.run_name in p.name
        and condition in p.name
    ]
    return sorted(candidates, key=lambda p: p.parent.name)[-1] if candidates else None


def _latest_legacy_csv(root: Path, row: RowSpec, condition: str) -> Path | None:
    legacy_dir = LEGACY_CONDITION_DIRS.get(condition)
    if legacy_dir is None or row.legacy_bench is None:
        return None

    search_root = root / legacy_dir / row.legacy_bench / "results"
    if row.legacy_bench == "rulearena_nba" and condition == "orch_seed_from_ptools":
        without_rulebook = search_root / "without_rulebook"
        if without_rulebook.is_dir():
            search_root = without_rulebook

    if not search_root.is_dir():
        return None

    candidates = [
        p
        for p in search_root.rglob("results.csv")
        if "with_rulebook" not in p.parts
    ]
    return sorted(candidates, key=lambda p: str(p.parent))[-1] if candidates else None


def find_csv(root: Path, row: RowSpec, condition: str) -> Path | None:
    if row.direct_csv is not None:
        direct = root / row.direct_csv
        if direct.exists():
            return direct

    canonical = _latest_canonical_csv(root, row, condition)
    if canonical is not None:
        return canonical

    return _latest_legacy_csv(root, row, condition)


def collect(root: Path) -> list[SummaryRow]:
    root = root.resolve()
    conditions, rows = ROOT_CONFIG[root.name]
    summaries = []
    for condition in conditions:
        for row in rows:
            path = find_csv(root, row, condition)
            experiment = f"{condition} / {row.label}"
            if path is None:
                summaries.append(SummaryRow(experiment, 0, math.nan, math.nan, None))
                continue
            n, accuracy, cost = summarize_csv(path)
            summaries.append(SummaryRow(experiment, n, accuracy, cost, path))
    return summaries


def fmt_accuracy(value: float) -> str:
    return f"{value:.1f}%" if math.isfinite(value) else "-"


def fmt_cost(value: float) -> str:
    return f"${value:.4f}" if math.isfinite(value) else "-"


def render(root: Path, rows: list[SummaryRow]) -> str:
    title = root.name
    label = " / ".join(CONDITION_LABELS[c] for c in ROOT_CONFIG[root.name][0])
    experiment_width = max(48, *(len(row.experiment) for row in rows))
    total_width = experiment_width + 35

    out = [
        "=" * total_width,
        title,
        label,
        "=" * total_width,
        f"{'Experiment':<{experiment_width}}  {'n':>6}  {'Accuracy':>9}  {'Cost':>12}",
        "-" * total_width,
    ]
    for row in rows:
        out.append(
            f"{row.experiment:<{experiment_width}}  "
            f"{row.n:>6}  {fmt_accuracy(row.accuracy):>9}  {fmt_cost(row.cost):>12}"
        )
    out.append("")
    out.append("Cost is the total reported cost across that experiment's result rows.")
    return "\n".join(out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        help="Result roots to summarize. Defaults to both orchestrator result roots.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roots = args.roots or [root for root in DEFAULT_ROOTS if root.is_dir()]

    unknown = [root for root in roots if root.name not in ROOT_CONFIG]
    if unknown:
        known = ", ".join(ROOT_CONFIG)
        names = ", ".join(str(path) for path in unknown)
        raise SystemExit(f"Unsupported result root(s): {names}. Expected one of: {known}")

    print()
    for idx, root in enumerate(roots):
        if idx:
            print()
        print(render(root.resolve(), collect(root)))
    print()


if __name__ == "__main__":
    main()
