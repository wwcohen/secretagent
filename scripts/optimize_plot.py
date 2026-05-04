#!/usr/bin/env python3
# /// script
# dependencies = ["pandas", "matplotlib"]
# ///
"""Plot optimization results: baselines vs NSGA-II summary.

Usage:
    uv run scripts/optimize_plot.py rulearena_nba
    uv run scripts/optimize_plot.py --output my_plot.png finqa
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OPTIMIZE_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "COMMON" / "optimize-results"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", help="Directory name under optimize-results/")
    parser.add_argument("--output", default=None, help="Output PNG file path (default: <benchmark>_optimize.png)")
    args = parser.parse_args()

    bench_dir = OPTIMIZE_DIR / args.benchmark
    if not bench_dir.is_dir():
        raise ValueError(f"Directory not found: {bench_dir}")

    output = args.output or f"{args.benchmark}_optimize.png"

    fig, ax = plt.subplots(figsize=(10, 7))

    # Load baselines
    baseline_points = []
    baselines_dir = bench_dir / "baselines"
    if baselines_dir.is_dir():
        for result_dir in sorted(baselines_dir.iterdir()):
            csv_path = result_dir / "results.csv"
            if not csv_path.exists():
                continue
            df = pd.read_csv(csv_path)
            if "cost" not in df.columns or "correct" not in df.columns:
                continue
            baseline_points.append((df["cost"].mean(), df["correct"].mean()))

    # Compute frontier for baselines: dominated if another has lower cost AND higher correct
    green_frontier = []
    for i, (x, y) in enumerate(baseline_points):
        dominated = any(
            ox < x and oy > y
            for j, (ox, oy) in enumerate(baseline_points) if j != i
        )
        marker = "s" if not dominated else "D"
        size = 12 if not dominated else 8
        ax.plot(x, y, marker=marker, color="green", markersize=size, alpha=0.6)
        if not dominated:
            green_frontier.append((x, y))

    # Legend entries for frontier markers
    if green_frontier:
        ax.plot([], [], marker="s", color="green", markersize=12, alpha=0.6,
                linestyle="None", label="baseline (frontier)")
    if baseline_points and len(baseline_points) > len(green_frontier):
        ax.plot([], [], marker="D", color="green", markersize=8, alpha=0.6,
                linestyle="None", label="baseline (dominated)")

    # Draw green frontier hull
    if len(green_frontier) >= 2:
        green_frontier.sort()
        gx, gy = zip(*green_frontier)
        ax.plot(gx, gy, color="green", linewidth=1, alpha=0.4)

    # Plot NSGA-II summary in blue
    blue_frontier = []
    summary_path = bench_dir / "nsga2_summary.csv"
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        for _, row in summary.iterrows():
            x = row["cost"]
            y = row["correct"]
            is_frontier = str(row.get("frontier", "")).strip().lower() == "true"
            marker = "o" if is_frontier else "."
            size = 12 if is_frontier else 8
            ax.plot(x, y, marker=marker, color="blue", markersize=size, alpha=0.6)
            if is_frontier:
                blue_frontier.append((x, y))

    # Legend entries for NSGA-II markers
    if blue_frontier:
        ax.plot([], [], marker="o", color="blue", markersize=12, alpha=0.6,
                linestyle="None", label="NSGA-II (frontier)")
    if summary_path.exists() and len(summary) > len(blue_frontier):
        ax.plot([], [], marker=".", color="blue", markersize=8, alpha=0.6,
                linestyle="None", label="NSGA-II (dominated)")

    # Draw blue frontier hull
    if len(blue_frontier) >= 2:
        blue_frontier.sort()
        bx, by = zip(*blue_frontier)
        ax.plot(bx, by, color="blue", linewidth=1, alpha=0.4)

    ax.legend(fontsize=12, loc="best")
    ax.set_xlabel("cost (minimize)", fontsize=14)
    ax.set_ylabel("correct (maximize)", fontsize=14)
    ax.set_title(f"{args.benchmark}: baselines vs NSGA-II", fontsize=16)
    ax.tick_params(labelsize=12)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"Plot saved to {output}")


if __name__ == "__main__":
    main()
