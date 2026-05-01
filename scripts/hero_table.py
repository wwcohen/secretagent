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

RESULTS_DIR = REPO_ROOT / "benchmarks" / "COMMON" / "results"

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
                # Report cost per 100 examples
                if metric == "cost":
                    mean *= 100
                    sem *= 100
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


_STRATEGY_MARKERS = ["o", "^", "s", "*", "D", "v", "P", "X"]


def _plot_comparison(df: pd.DataFrame, metric: str,
                     x_strategy: str | list[str] = "react",
                     y_strategy: str = "workflow", output: str = "hero_plot.png"):
    """Plot y_strategy vs x_strategy(ies) on a given metric with error boxes.

    When x_strategy is a list, each strategy gets a distinct marker shape
    and benchmarks are distinguished by color.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    if isinstance(x_strategy, str):
        x_strategy = [x_strategy]

    fig, ax = plt.subplots(figsize=(10, 7))

    # Assign a persistent color per task across all x strategies
    task_colors = {}
    color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for si, x_strat in enumerate(x_strategy):
        marker = _STRATEGY_MARKERS[si % len(_STRATEGY_MARKERS)]
        for task in df.index:
            wf = _parse_cell(df.loc[task, y_strategy])
            xs = _parse_cell(df.loc[task, x_strat])
            if wf is None or xs is None:
                continue

            x_mean, x_sem = xs
            y_mean, y_sem = wf

            if task not in task_colors:
                task_colors[task] = color_cycle[len(task_colors) % len(color_cycle)]
            color = task_colors[task]

            # Label: show task name only for first strategy, strategy name only when multiple
            if len(x_strategy) == 1:
                label = task
            elif si == 0:
                label = f"{task} ({x_strat})"
            else:
                label = f"{task} ({x_strat})"

            ax.plot(x_mean, y_mean, marker=marker, markersize=7,
                    color=color, label=label)
            rect = Rectangle(
                (x_mean - x_sem, y_mean - y_sem),
                2 * x_sem, 2 * y_sem,
                linewidth=1, edgecolor=color, facecolor=color, alpha=0.15,
            )
            ax.add_patch(rect)

    # y=x reference line
    lo = min(ax.get_xlim()[0], ax.get_ylim()[0])
    hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.plot([lo, hi], [lo, hi], "k--", linewidth=0.8, alpha=0.5)

    # Add marker legend entries for strategies when multiple x strategies
    if len(x_strategy) > 1:
        from matplotlib.lines import Line2D
        strategy_handles = []
        for si, x_strat in enumerate(x_strategy):
            marker = _STRATEGY_MARKERS[si % len(_STRATEGY_MARKERS)]
            strategy_handles.append(
                Line2D([0], [0], marker=marker, color="gray", linestyle="None",
                       markersize=7, label=x_strat))
        # Task color handles
        task_handles = [
            Line2D([0], [0], marker="o", color=c, linestyle="None",
                   markersize=7, label=t)
            for t, c in task_colors.items()
        ]
        ax.legend(handles=strategy_handles + task_handles, fontsize=8, loc="best")
        x_label = "/".join(x_strategy)
    else:
        ax.legend(fontsize=8, loc="best")
        x_label = x_strategy[0]

    ax.set_xlabel(f"{x_label} {metric}")
    ax.set_ylabel(f"{y_strategy} {metric}")
    ax.set_title(f"{y_strategy} vs {x_label} {metric}")
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


_COMPACT_STRATEGIES = ["workflow", "react", "structured_baseline"]


def _print_latex_compact(correct_df: pd.DataFrame, cost_df: pd.DataFrame,
                         caption: str = "Correctness and Cost (per 100 examples)"):
    """Print a compact LaTeX table with correctness on the left and cost on the right."""
    strats = _COMPACT_STRATEGIES
    headers_correct = " & ".join(_LATEX_HEADERS.get(s, s.replace("_", r"\_")) for s in strats)
    headers_cost = " & ".join(_LATEX_HEADERS.get(s, s.replace("_", r"\_")) for s in strats)

    # Use cost_df index as it may have extra summary rows (e.g. AVERAGE_EXCL_TAU)
    tasks = cost_df.index

    col_spec = "l" + "c" * len(strats) + "|" + "c" * len(strats)
    print(r"\begin{table*}[ht]")
    print(r"\centering")
    print(r"\small")
    print(r"\begin{tabular}{" + col_spec + "}")
    print(r"\toprule")
    print(r" & \multicolumn{" + str(len(strats)) + r"}{c}{Correctness} & \multicolumn{"
          + str(len(strats)) + r"}{c}{Cost (per 100 examples)} \\")
    print(r"\cmidrule(lr){2-" + str(1 + len(strats)) + r"} \cmidrule(lr){"
          + str(2 + len(strats)) + "-" + str(1 + 2 * len(strats)) + "}")
    print(r"Task & " + headers_correct + " & " + headers_cost + r" \\")
    print(r"\midrule")

    for task in tasks:
        # Correctness cells (bold = max)
        parsed_correct = {s: _parse_cell(correct_df.loc[task, s]) for s in strats if s in correct_df.columns} if task in correct_df.index else {}
        correct_means = [p[0] for p in parsed_correct.values() if p is not None]
        best_correct = max(correct_means) if correct_means else None
        cells_correct = []
        for s in strats:
            p = parsed_correct.get(s)
            if p is None:
                cells_correct.append("--")
            else:
                mean, sem = p
                if mean == best_correct:
                    cells_correct.append(f"$\\mathbf{{{mean:.2f}}}$")
                else:
                    cells_correct.append(f"${mean:.2f}$")

        # Cost cells (bold = min)
        parsed_cost = {s: _parse_cell(cost_df.loc[task, s]) for s in strats if s in cost_df.columns}
        cost_means = [p[0] for p in parsed_cost.values() if p is not None]
        best_cost = min(cost_means) if cost_means else None
        cells_cost = []
        for s in strats:
            p = parsed_cost.get(s)
            if p is None:
                cells_cost.append("--")
            else:
                mean, sem = p
                if mean == best_cost:
                    cells_cost.append(f"$\\mathbf{{{mean:.2f}}}$")
                else:
                    cells_cost.append(f"${mean:.2f}$")

        task_label = task.replace("_", r"\_")
        if task == "AVERAGE":
            print(r"\midrule")
            task_label = r"\textrm{Average}"
        elif task == "AVERAGE_EXCL_TAU":
            task_label = r"\hspace{10pt}\textrm{without $\tau$ Bench}"
            cells_correct = [""] * len(strats)
        else:
            task_label = TASK_TO_LATEX.get(task, task.replace("_", r"\_"))
        print(task_label + " & " + " & ".join(cells_correct) + " & " + " & ".join(cells_cost) + r" \\")

    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\caption{" + caption + "}")
    print(r"\end{table*}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-cols", type=int, default=0,
                        help="Suppress rows with fewer than K populated columns")
    parser.add_argument("--format", choices=["table", "plot-correct", "plot-cost", "latex-correct", "latex-cost", "latex-compact"], default="table",
                        help="Output format: table (default), plot-correct, plot-cost, latex-correct, latex-cost, or latex-compact")
    parser.add_argument("--output", default="hero_plot.png",
                        help="Output PNG file path (for plot-correct)")
    parser.add_argument("--x", nargs="+", default=["react"],
                        help="Strategy(ies) for x-axis in plot modes (default: react)")
    parser.add_argument("--y", default="workflow",
                        choices=STRATEGY_ORDER,
                        help="Strategy for y-axis in plot modes (default: workflow)")
    parser.add_argument("--suppress", nargs="+", default=[],
                        metavar="TASK",
                        help="Benchmarks to exclude (e.g. tau_bench/retail)")
    args = parser.parse_args()

    cost_df, correct_df = build_tables()

    if args.suppress:
        cost_df = cost_df[~cost_df.index.isin(args.suppress)]
        correct_df = correct_df[~correct_df.index.isin(args.suppress)]

    if args.min_cols > 0:
        cost_df = _filter_min_cols(cost_df, args.min_cols)
        correct_df = _filter_min_cols(correct_df, args.min_cols)

    if args.format == "latex-correct":
        correct_df = pd.concat([correct_df, _avg_row(correct_df, "AVERAGE")])
        _print_latex(correct_df, "Correctness")
        return

    if args.format == "latex-compact":
        correct_df = pd.concat([correct_df, _avg_row(correct_df, "AVERAGE")])
        cost_df = pd.concat([
            cost_df,
            _avg_row(cost_df, "AVERAGE"),
            _avg_row(cost_df, "AVERAGE_EXCL_TAU", exclude_prefix="tau_bench/"),
        ])
        _print_latex_compact(correct_df, cost_df)
        return

    if args.format == "latex-cost":
        cost_df = pd.concat([
            cost_df,
            _avg_row(cost_df, "AVERAGE"),
            _avg_row(cost_df, "AVERAGE_EXCL_TAU", exclude_prefix="tau_bench/"),
        ])
        _print_latex(cost_df, "Cost (per 100 examples)", minimize=True)
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
    print("=== Cost (per 100 examples) ===")
    print(cost_df.to_string())


if __name__ == "__main__":
    main()
