"""Regenerate nsga2.png from nsga2_summary.csv in this directory.

Run from anywhere in a checked-out repo:

    uv run benchmarks/COMMON/optimize-results/rulearena_nba/plot.py

Reads `nsga2_summary.csv` next to this script and writes `nsga2.png`
next to this script. Uses the project's shared viz module so the
plot styling tracks any future improvements to the optimizer's plots.
"""
from pathlib import Path

import pandas as pd

from secretagent.optimize.viz import plot_pareto_frontier


HERE = Path(__file__).parent


def main() -> None:
    df = pd.read_csv(HERE / "nsga2_summary.csv")
    df = df[df["valid"]].copy()
    results = [(row["config"], row["correct"], row["cost"]) for _, row in df.iterrows()]
    plot_pareto_frontier(
        results=results,
        title="Cost vs correct (NSGA-II) — RuleArena NBA",
        output_path=HERE / "nsga2.png",
        metric_name="correct",
        show=False,
    )


if __name__ == "__main__":
    main()
