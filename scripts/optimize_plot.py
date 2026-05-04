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


def load_points_from_dirs(parent_dir):
    """Load (cost, correct) points from results.csv files in subdirectories."""
    points = []
    if not parent_dir.is_dir():
        return points
    for result_dir in sorted(parent_dir.iterdir()):
        csv_path = result_dir / "results.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        if "cost" not in df.columns or "correct" not in df.columns:
            continue
        points.append((df["cost"].mean(), df["correct"].mean()))
    return points


def compute_frontier(points):
    """Return list of bools: True if point is on the Pareto frontier."""
    frontier = []
    for i, (x, y) in enumerate(points):
        dominated = any(
            ox < x and oy > y
            for j, (ox, oy) in enumerate(points) if j != i
        )
        frontier.append(not dominated)
    return frontier


def plot_points(ax, points, frontier, color, frontier_marker, dominated_marker, label=""):
    """Plot points with different markers for frontier vs dominated."""
    for (x, y), on_frontier in zip(points, frontier):
        marker = frontier_marker if on_frontier else dominated_marker
        size = 12 if on_frontier else 8
        ax.plot(x, y, marker=marker, color=color, markersize=size, alpha=0.6)

    # Legend entries
    if any(frontier):
        ax.plot([], [], marker=frontier_marker, color=color, markersize=12, alpha=0.6,
                linestyle="None", label=f"{label} (frontier)")
    if not all(frontier):
        ax.plot([], [], marker=dominated_marker, color=color, markersize=8, alpha=0.6,
                linestyle="None", label=f"{label} (dominated)")

    # Draw frontier hull
    frontier_pts = sorted(p for p, f in zip(points, frontier) if f)
    if len(frontier_pts) >= 2:
        fx, fy = zip(*frontier_pts)
        ax.plot(fx, fy, color=color, linewidth=1, alpha=0.4)


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

    # Load and plot baselines (green)
    baseline_points = load_points_from_dirs(bench_dir / "baselines")
    if baseline_points:
        baseline_frontier = compute_frontier(baseline_points)
        plot_points(ax, baseline_points, baseline_frontier, "green", "s", "D", "baseline")

    # Load and plot NSGA-II runs (blue)
    nsga_points = load_points_from_dirs(bench_dir / "nsga_runs")
    if nsga_points:
        nsga_frontier = compute_frontier(nsga_points)
        plot_points(ax, nsga_points, nsga_frontier, "blue", "o", ".", "NSGA-II")

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
