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

OPTIMIZE_DIR = Path(__file__).resolve().parent.parent / "paper" / "results" / "optimize-results"


def load_points_from_dirs(parent_dir):
    """Load (cost, correct, dir_name) tuples from results.csv files in subdirectories."""
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
        points.append((df["cost"].mean(), df["correct"].mean(), result_dir.name))
    return points


def strip_timestamp(name):
    """Strip the YYYYMMDD.HHMMSS. prefix from a directory name."""
    parts = name.split(".", 2)
    if len(parts) >= 3:
        return parts[2]
    return name


def compute_frontier(points):
    """Return list of bools: True if point is on the Pareto frontier.

    Points are (cost, correct, name) tuples.
    """
    frontier = []
    for i, (x, y, _) in enumerate(points):
        dominated = any(
            ox < x and oy > y
            for j, (ox, oy, _) in enumerate(points) if j != i
        )
        frontier.append(not dominated)
    return frontier


def plot_points(ax, points, frontier, color, frontier_marker, dominated_marker, label=""):
    """Plot points with different markers for frontier vs dominated."""
    for (x, y, _), on_frontier in zip(points, frontier):
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
    frontier_pts = sorted((x, y) for (x, y, _), f in zip(points, frontier) if f)
    if len(frontier_pts) >= 2:
        fx, fy = zip(*frontier_pts)
        ax.plot(fx, fy, color=color, linewidth=1, alpha=0.4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", help="Directory name under optimize-results/")
    parser.add_argument("--output", default=None, help="Output PNG file path (default: <benchmark>_optimize.png)")
    parser.add_argument("--points-of-interest", type=int, default=0, metavar="K",
                        help="Annotate K points of interest on the NSGA-II frontier")
    parser.add_argument("--downshift", type=float, default=0.75,
                        help="Top label y position as fraction of max correctness (default: 0.75)")
    parser.add_argument("--label", nargs="+", default=None,
                        help="Override labels for points of interest (in order)")
    parser.add_argument("--spacer", type=float, default=0.05,
                        help="Vertical spacing between labels (default: 0.05)")
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

    # Points of interest
    if args.points_of_interest >= 2 and nsga_points:
        import math
        frontier_pts = [(x, y, name) for (x, y, name), f in zip(nsga_points, nsga_frontier) if f]
        if len(frontier_pts) >= 2:
            # Point 1: highest correctness (listed first)
            pt1 = max(frontier_pts, key=lambda p: p[1])
            # Point 2: lowest cost (listed last)
            pt2 = min(frontier_pts, key=lambda p: p[0])

            # Midpoint between pt1 and pt2
            mid_x = (pt1[0] + pt2[0]) / 2
            mid_y = (pt1[1] + pt2[1]) / 2

            # Select K-2 closest to midpoint from remaining frontier points
            remaining = [p for p in frontier_pts if p not in (pt1, pt2)]
            remaining.sort(key=lambda p: math.hypot(p[0] - mid_x, p[1] - mid_y))
            selected = [pt1] + remaining[:max(0, args.points_of_interest - 2)] + [pt2]

            # Place labels above the legend area (upper-right region)
            # Use figure transform to position text
            if args.label and len(args.label) >= len(selected):
                labels = args.label[:len(selected)]
            elif args.label:
                labels = args.label + [strip_timestamp(name) for _, _, name in selected[len(args.label):]]
            else:
                labels = [strip_timestamp(name) for _, _, name in selected]
            label_x = 0.70  # right region in axes coords, left-aligned text extends rightward
            y_max = max(y for _, y, _ in frontier_pts)
            label_y_start = args.downshift * y_max
            label_spacing = args.spacer * y_max

            for idx, ((px, py, _), label_text) in enumerate(zip(selected, labels)):
                text_y = label_y_start - idx * label_spacing
                ax.annotate(
                    label_text,
                    xy=(px, py),
                    xytext=(label_x, text_y),
                    textcoords=("axes fraction", "data"),
                    fontsize=13,
                    color="black",
                    ha="left",
                    arrowprops=dict(
                        arrowstyle="->",
                        color="black",
                        linestyle="dotted",
                        lw=1.5,
                    ),
                )

    ax.legend(fontsize=12, loc="lower right")
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
