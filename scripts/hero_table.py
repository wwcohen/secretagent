#!/usr/bin/env python3
"""Build hero tables of cost and correctness across tasks and strategies.

For each task in benchmark_status.TASKS, loads the latest result
directory for each strategy and computes mean +/- sem for cost and
correctness.  Prints two DataFrames: one for correctness, one for cost.

Usage:

    # print tables (suppress rows with fewer than 3 strategies)
    uv run scripts/hero_table.py --min-cols 3

    # scatter plot: workflow (y) vs react (x) correctness
    uv run scripts/hero_table.py --format plot-correct --min-cols 3

    # scatter plot: workflow (y) vs pot (x) correctness
    uv run scripts/hero_table.py --format plot-correct --x pot --min-cols 3

    # scatter plot: react (y) vs pot (x) correctness
    uv run scripts/hero_table.py --format plot-correct --x pot --y react --min-cols 3

    # scatter plot: workflow (y) vs react (x) cost
    uv run scripts/hero_table.py --format plot-cost --output cost_plot.png
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from benchmark_status import TASKS, STRATEGIES, RESULT_DIR_RE, TASK_TO_LATEX

RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"

STRATEGY_ORDER = ["workflow", "react", "pot", "structured_baseline", "unstructured_baseline"]


def find_latest_result_dir(parent: Path, strategy: str) -> Path | None:
    """Find the latest result directory for a strategy under parent."""
    if not parent.is_dir():
        return None
    matches = []
    for d in parent.iterdir():
        if not d.is_dir():
            continue
        m = RESULT_DIR_RE.match(d.name)
        if m and m.group(1) == strategy:
            matches.append(d)
    if not matches:
        return None
    return sorted(matches)[-1]


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build cost and correctness DataFrames across tasks and strategies.

    Returns (cost_df, correct_df) with tasks as rows and strategies as columns.
    Cell values are formatted as "mean +/- sem".
    """
    cost_rows = []
    correct_rows = []

    for task_subtask in TASKS:
        task, subtask = task_subtask.split("/")
        parent = RESULTS_DIR / task / subtask

        cost_row = {"task": task_subtask}
        correct_row = {"task": task_subtask}

        for strategy in STRATEGY_ORDER:
            result_dir = find_latest_result_dir(parent, strategy)
            if result_dir is None:
                cost_row[strategy] = ""
                correct_row[strategy] = ""
                continue

            csv_path = result_dir / "results.csv"
            if not csv_path.exists():
                cost_row[strategy] = ""
                correct_row[strategy] = ""
                continue

            df = pd.read_csv(csv_path)

            for metric, row in [("cost", cost_row), ("correct", correct_row)]:
                if metric not in df.columns:
                    row[strategy] = ""
                    continue
                mean = df[metric].mean()
                sem = df[metric].sem()
                row[strategy] = f"{mean:.4f} +/- {sem:.4f}"

        cost_rows.append(cost_row)
        correct_rows.append(correct_row)

    cost_df = pd.DataFrame(cost_rows).set_index("task")[STRATEGY_ORDER]
    correct_df = pd.DataFrame(correct_rows).set_index("task")[STRATEGY_ORDER]
    return cost_df, correct_df


def _avg_row(df: pd.DataFrame, label: str, exclude_prefix: str | None = None) -> pd.DataFrame:
    """Compute an average row from a table of "mean +/- sem" strings.

    Extracts the mean values, averages across tasks, and returns a
    single-row DataFrame with the same columns.
    """
    subset = df
    if exclude_prefix:
        subset = df[~df.index.str.startswith(exclude_prefix)]

    row = {"task": label}
    for col in df.columns:
        vals = []
        for cell in subset[col]:
            if cell and "+/-" in str(cell):
                vals.append(float(cell.split("+/-")[0].strip()))
        if vals:
            avg = np.mean(vals)
            se = np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0.0
            row[col] = f"{avg:.4f} +/- {se:.4f}"
        else:
            row[col] = ""
    return pd.DataFrame([row]).set_index("task")


def _filter_min_cols(df: pd.DataFrame, min_cols: int) -> pd.DataFrame:
    """Keep only rows with at least min_cols non-empty cells."""
    populated = df.apply(lambda row: sum(1 for v in row if v and str(v).strip()), axis=1)
    return df[populated >= min_cols]


def _parse_cell(cell: str) -> tuple[float, float] | None:
    """Parse a "mean +/- sem" cell, returning (mean, sem) or None."""
    if not cell or "+/-" not in str(cell):
        return None
    parts = str(cell).split("+/-")
    return float(parts[0].strip()), float(parts[1].strip())


def _plot_comparison(df: pd.DataFrame, metric: str, x_strategy: str = "react",
                     y_strategy: str = "workflow", output: str = "hero_plot.png"):
    """Plot workflow vs another strategy on a given metric with error boxes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(figsize=(10, 7))

    for task in df.index:
        wf = _parse_cell(df.loc[task, y_strategy])
        xs = _parse_cell(df.loc[task, x_strategy])
        if wf is None or xs is None:
            continue

        x_mean, x_sem = xs
        y_mean, y_sem = wf

        ax.plot(x_mean, y_mean, "o", markersize=6, label=task)
        color = ax.lines[-1].get_color()
        rect = Rectangle(
            (x_mean - x_sem, y_mean - y_sem),
            2 * x_sem, 2 * y_sem,
            linewidth=1, edgecolor=color, facecolor=color, alpha=0.25,
        )
        ax.add_patch(rect)

    # y=x reference line
    lo = min(ax.get_xlim()[0], ax.get_ylim()[0])
    hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.plot([lo, hi], [lo, hi], "k--", linewidth=0.8, alpha=0.5)

    ax.set_xlabel(f"{x_strategy} {metric}")
    ax.set_ylabel(f"{y_strategy} {metric}")
    ax.set_title(f"{y_strategy} vs {x_strategy} {metric}")
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"Plot saved to {output}")


_LATEX_HEADERS = {
    "workflow": r"\makecell{Static\\Workflow}",
    "react": r"\makecell{Dynamic\\Workflow\\(ReAct)}",
    "pot": r"\makecell{Dynamic\\Workflow\\(PoT)}",
    "structured_baseline": r"\makecell{Zero-shot\\(Default\\Imp.)}",
    "unstructured_baseline": r"\makecell{Zero-shot\\(Custom\\Prompt)}",
}


def _print_latex(df: pd.DataFrame, caption: str, minimize: bool = False):
    """Print a LaTeX table from a \"mean +/- sem\" DataFrame."""
    cols = df.columns.tolist()
    header_cols = " & ".join(_LATEX_HEADERS.get(c, c.replace("_", r"\_")) for c in cols)
    print(r"\begin{table*}[ht]")
    print(r"\centering")
    print(r"\begin{tabular}{l" + "c" * len(cols) + "}")
    print(r"\toprule")
    print(r"Task & " + header_cols + r" \\")
    print(r"\midrule")
    for task in df.index:
        parsed_row = {col: _parse_cell(df.loc[task, col]) for col in cols}
        means = [p[0] for p in parsed_row.values() if p is not None]
        best = (min(means) if minimize else max(means)) if means else None
        cells = []
        for col in cols:
            p = parsed_row[col]
            if p is None:
                cells.append("--")
            else:
                mean, sem = p
                if mean == best:
                    cell = f"$\\mathbf{{{mean:.2f}}}$"
                else:
                    cell = f"${mean:.2f}$"
                cells.append(cell)
        task_label = task.replace("_", r"\_")
        if task == "AVERAGE":
            print(r"\midrule")
            task_label = r"\textrm{Average}"
        else:
            task_label = TASK_TO_LATEX.get(task, task.replace("_", r"\_"))
        print(task_label + " & " + " & ".join(cells) + r" \\")
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\caption{" + caption + "}")
    print(r"\end{table*}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-cols", type=int, default=0,
                        help="Suppress rows with fewer than K populated columns")
    parser.add_argument("--format", choices=["table", "plot-correct", "plot-cost", "latex-correct", "latex-cost"], default="table",
                        help="Output format: table (default), plot-correct, plot-cost, latex-correct, or latex-cost")
    parser.add_argument("--output", default="hero_plot.png",
                        help="Output PNG file path (for plot-correct)")
    parser.add_argument("--x", default="react",
                        choices=STRATEGY_ORDER,
                        help="Strategy for x-axis in plot modes (default: react)")
    parser.add_argument("--y", default="workflow",
                        choices=STRATEGY_ORDER,
                        help="Strategy for y-axis in plot modes (default: workflow)")
    args = parser.parse_args()

    cost_df, correct_df = build_tables()

    if args.min_cols > 0:
        cost_df = _filter_min_cols(cost_df, args.min_cols)
        correct_df = _filter_min_cols(correct_df, args.min_cols)

    if args.format == "latex-correct":
        correct_df = pd.concat([correct_df, _avg_row(correct_df, "AVERAGE")])
        _print_latex(correct_df, "Correctness")
        return

    if args.format == "latex-cost":
        cost_df = pd.concat([
            cost_df,
            _avg_row(cost_df, "AVERAGE"),
            _avg_row(cost_df, "AVERAGE_EXCL_TAU", exclude_prefix="tau_bench/"),
        ])
        _print_latex(cost_df, "Cost", minimize=True)
        return

    if args.format == "plot-correct":
        _plot_comparison(correct_df, "correctness", x_strategy=args.x, y_strategy=args.y, output=args.output)
        return

    if args.format == "plot-cost":
        _plot_comparison(cost_df, "cost", x_strategy=args.x, y_strategy=args.y, output=args.output)
        return

    correct_df = pd.concat([correct_df, _avg_row(correct_df, "AVERAGE")])
    cost_df = pd.concat([
        cost_df,
        _avg_row(cost_df, "AVERAGE"),
        _avg_row(cost_df, "AVERAGE (excl tau_bench)", exclude_prefix="tau_bench/"),
    ])

    print("=== Correctness ===")
    print(correct_df.to_string())
    print()
    print("=== Cost ===")
    print(cost_df.to_string())


if __name__ == "__main__":
    main()
