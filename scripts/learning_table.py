#!/usr/bin/env python3
# /// script
# dependencies = ["pandas"]
# ///
"""Build tables of results of various learning/engineering/optimization methods."""

import os
import glob

import pandas as pd

KEYTASKS = [
    "musr/murder",
    "musr/object",
    "musr/team",
    "natural_plan/meeting",
    "natural_plan/trip",
    "rulearena/nba",
    "medcalc/overall",
    "medcalc/formula",
    "medcalc/rules",
]

BASE = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "COMMON")
RESULTS_DIR = os.path.join(BASE, "results")
CODEDISTILL_DIR = os.path.join(BASE, "codedistill-workflow-results")
LEARNER_DIR = os.path.join(BASE, "learner-results")


def read_csv(csv_path):
    """Read a results CSV as a DataFrame with correct as float."""
    df = pd.read_csv(csv_path)
    col = df["correct"]
    if col.dtype == object:
        col = col.map({"True": 1.0, "true": 1.0, "False": 0.0, "false": 0.0})
    df["correct"] = col.astype(float)
    return df


def find_latest_dir(directory, pattern):
    """Find the latest (by name sort) directory matching a glob pattern."""
    matches = sorted(glob.glob(os.path.join(directory, pattern)))
    if matches:
        return matches[-1]
    return None


def find_workflow_csv(task, subtask):
    """Find workflow results CSV for a task/subtask."""
    subtask_dir = os.path.join(RESULTS_DIR, task, subtask)
    if not os.path.isdir(subtask_dir):
        return None
    # Try DATE.TIME.workflow first
    result = find_latest_dir(subtask_dir, "*.workflow")
    if not result:
        # Try DATE.TIME.SUBTASK_workflow
        result = find_latest_dir(subtask_dir, f"*.{subtask}_workflow")
    if result:
        csv_path = os.path.join(result, "results.csv")
        if os.path.isfile(csv_path):
            return csv_path
    return None


def find_codedistill_csv(task, subtask, learner_llm="opus", ptool_class="class2"):
    """Find codedistill workflow results CSV for a task/subtask."""
    task_dir = os.path.join(CODEDISTILL_DIR, task, "test_results_full")
    if not os.path.isdir(task_dir):
        return None
    # Pattern: DATE.TIME.*SUBTASK_test_full_CLASS_LEARNER_cache
    result = find_latest_dir(task_dir, f"*{subtask}_test_full_{ptool_class}_{learner_llm}_cache")
    if result:
        csv_path = os.path.join(result, "results.csv")
        if os.path.isfile(csv_path):
            return csv_path
    return None


def find_react_csv(task, subtask):
    """Find ReAct results CSV for a task/subtask."""
    subtask_dir = os.path.join(RESULTS_DIR, task, subtask)
    if not os.path.isdir(subtask_dir):
        return None
    result = find_latest_dir(subtask_dir, "*react_engineered")
    if result:
        csv_path = os.path.join(result, "results.csv")
        if os.path.isfile(csv_path):
            return csv_path
    return None


def find_react_learned_csv(task, subtask):
    """Find ReAct/learned results CSV for a task/subtask in learner-results."""
    subtask_dir = os.path.join(LEARNER_DIR, task, subtask)
    if not os.path.isdir(subtask_dir):
        return None
    result = find_latest_dir(subtask_dir, f"*{subtask}_induced*")
    if result:
        csv_path = os.path.join(result, "results.csv")
        if os.path.isfile(csv_path):
            return csv_path
    return None


ORCHESTRATOR_DIR = os.path.join(BASE, "orchestrator-results")
ORCHESTRATOR_INDUCED_DIR = os.path.join(BASE, "orchestrator-induced-ptools-results")


def _find_orchestrator_csv(base_dir, task, subtask, suffix):
    """Find orchestrator results CSV, mirroring find_codedistill_csv layout."""
    task_dir = os.path.join(base_dir, task, "test_results_full")
    if not os.path.isdir(task_dir):
        return None
    result = find_latest_dir(task_dir, f"*{subtask}_test_full_{suffix}")
    if result:
        csv_path = os.path.join(result, "results.csv")
        if os.path.isfile(csv_path):
            return csv_path
    return None


def find_orchestrator_human_csv(task, subtask):
    """Find orchestrator results CSV with human ptools."""
    return _find_orchestrator_csv(ORCHESTRATOR_DIR, task, subtask,
                                  "orch_seed_from_ptools")


def find_orchestrator_learned_csv(task, subtask):
    """Find orchestrator results CSV with induced/learned ptools."""
    return _find_orchestrator_csv(ORCHESTRATOR_INDUCED_DIR, task, subtask,
                                  "orch_induced_seed_ptools")


def find_optimizer_csv(task, subtask):
    """Find best NSGA-II test-pass results CSV for a task/subtask.

    Scans paper/results/results/<task>/<subtask>/*.test_pass_* for the
    Pareto-frontier configurations exported from the optimizer pipeline,
    and returns the CSV path of the configuration with the highest
    mean(correct) on test (Pareto top-1 by accuracy)."""
    subtask_dir = os.path.join(RESULTS_DIR, task, subtask)
    if not os.path.isdir(subtask_dir):
        return None
    matches = sorted(glob.glob(os.path.join(subtask_dir, "*.test_pass_*")))
    if not matches:
        return None
    best_csv = None
    best_acc = -1.0
    for d in matches:
        csv_path = os.path.join(d, "results.csv")
        if not os.path.isfile(csv_path):
            continue
        try:
            acc = read_csv(csv_path)["correct"].mean()
        except Exception:
            continue
        if acc > best_acc:
            best_acc = acc
            best_csv = csv_path
    return best_csv


def format_cell(series):
    """Format mean +/- sem from a pandas Series."""
    if series is None or series.empty:
        return "—"
    m = series.mean()
    s = series.sem()
    return f"{m:.2f}+/-{s:.2f}"


def _add_row(correct_rows, cost_rows, label_cols, col_names, find_fn, tasks):
    """Add a row to both correct and cost tables using find_fn to locate CSVs."""
    correct_row = dict(label_cols)
    cost_row = dict(label_cols)
    for keytask, col in zip(tasks, col_names):
        task, subtask = keytask.split("/")
        csv_path = find_fn(task, subtask)
        if csv_path:
            df = read_csv(csv_path)
            correct_row[col] = format_cell(df["correct"])
            if "cost" in df.columns:
                cost_row[col] = format_cell(df["cost"] * 100)
            else:
                cost_row[col] = "—"
        else:
            correct_row[col] = "—"
            cost_row[col] = "—"
    correct_rows.append(correct_row)
    cost_rows.append(cost_row)


def build_dataframes(include_opus=False, suppress_tasks=None, suppress_rows=None, transpose=False):
    """Build DataFrames for correctness and cost (USD per 100 examples)."""
    tasks = [t for t in KEYTASKS if t not in (suppress_tasks or [])]
    suppress_rows = set(suppress_rows or [])
    col_names = [
        f"{t.split('/')[0].replace('natural_plan', 'natplan')}/{t.split('/')[1]}"
        for t in tasks
    ]
    correct_rows = []
    cost_rows = []

    # Row 1: engineered workflow
    _add_row(correct_rows, cost_rows,
             {"workflow": "human", "model": "-", "toolkit": "human"},
             col_names, find_workflow_csv, tasks)

    # Row 2: ReAct with human toolkit
    _add_row(correct_rows, cost_rows,
             {"workflow": "ReAct", "model": "-", "toolkit": "human"},
             col_names, find_react_csv, tasks)

    # Row 3: ReAct / Deepseek-V3 / learned
    _add_row(correct_rows, cost_rows,
             {"workflow": "ReAct", "model": "Deepseek-V3", "toolkit": "learned"},
             col_names, find_react_learned_csv, tasks)

    # Codedistill rows: learner_llm x ptool_class
    toolkit_labels = {"class2": "human", "class3": "learned"}
    learner_llms = ("opus", "gemini") if include_opus else ("gemini",)
    for learner_llm in learner_llms:
        for ptool_class in ("class2", "class3"):
            label = {"workflow": "codedist", "model": learner_llm, "toolkit": toolkit_labels[ptool_class]}
            _add_row(correct_rows, cost_rows, label, col_names,
                     lambda t, s, ll=learner_llm, pc=ptool_class: find_codedistill_csv(t, s, learner_llm=ll, ptool_class=pc),
                     tasks)

    # Orchestrator with human ptools row
    _add_row(correct_rows, cost_rows,
             {"workflow": "orchest", "model": "-", "toolkit": "human"},
             col_names, find_orchestrator_human_csv, tasks)

    # Orchestrator with learned/induced ptools row
    _add_row(correct_rows, cost_rows,
             {"workflow": "orchest", "model": "-", "toolkit": "learned"},
             col_names, find_orchestrator_learned_csv, tasks)

    # Optimizer row: NSGA-II Pareto top-1 by test accuracy.
    _add_row(correct_rows, cost_rows,
             {"workflow": "nsga", "model": "auto", "toolkit": "auto"},
             col_names, find_optimizer_csv, tasks)

    correct_df = pd.DataFrame(correct_rows)
    cost_df = pd.DataFrame(cost_rows)

    if suppress_rows:
        key = correct_df["workflow"] + "/" + correct_df["toolkit"]
        mask = ~key.isin(suppress_rows)
        correct_df = correct_df[mask].reset_index(drop=True)
        cost_df = cost_df[mask].reset_index(drop=True)

    if transpose:
        # Tasks as rows, methods as columns
        label_cols = ["workflow", "model", "toolkit"]
        for df in (correct_df, cost_df):
            if include_opus:
                df.index = df.apply(lambda r: f"{r['workflow']}/{r['model']}/{r['toolkit']}", axis=1)
            else:
                df.index = df.apply(lambda r: f"{r['workflow']}/{r['toolkit']}", axis=1)
            df.drop(columns=label_cols, inplace=True)

        correct_df = correct_df.T
        cost_df = cost_df.T

        # Add average row
        for df in (correct_df, cost_df):
            avgs = {}
            for col in df.columns:
                vals = [float(c.split("+/-")[0]) for c in df[col] if isinstance(c, str) and "+/-" in c]
                avgs[col] = f"{sum(vals)/len(vals):.2f}" if vals else "—"
            df.loc["average"] = avgs
    else:
        # Methods as rows, tasks as columns (with workflow and ptools label columns)
        drop_cols = ["model"] if not include_opus else []
        for df in (correct_df, cost_df):
            df.rename(columns={"toolkit": "ptools"}, inplace=True)
            if drop_cols:
                df.drop(columns=drop_cols, inplace=True)

        # Add average column
        task_cols = col_names
        for df in (correct_df, cost_df):
            avgs = []
            for _, row in df.iterrows():
                vals = [float(row[c].split("+/-")[0]) for c in task_cols if isinstance(row[c], str) and "+/-" in row[c]]
                avgs.append(f"{sum(vals)/len(vals):.2f}" if vals else "—")
            df["average"] = avgs

    return correct_df, cost_df


def _parse_cell(cell):
    """Parse a 'mean+/-sem' or plain number cell, returning (mean, sem) or None."""
    if not isinstance(cell, str):
        return None
    if "+/-" in cell:
        parts = cell.split("+/-")
        return float(parts[0].strip()), float(parts[1].strip())
    try:
        return float(cell.strip()), 0.0
    except ValueError:
        return None


def _print_latex(df, caption, minimize=False, transpose=False):
    """Print a LaTeX table from a DataFrame with 'mean+/-sem' cells.

    Bold the best value in each task column (max for correctness, min for cost).
    """
    if transpose:
        # tasks are rows, methods are columns
        task_cols = list(df.columns)
        print(r"\begin{table*}[ht]")
        print(r"\centering")
        print(r"\begin{tabular}{l" + "c" * len(task_cols) + "}")
        print(r"\toprule")
        print("Task & " + " & ".join(c.replace("_", r"\_") for c in task_cols) + r" \\")
        print(r"\midrule")
        for task in df.index:
            parsed = {c: _parse_cell(df.loc[task, c]) for c in task_cols}
            means = [p[0] for p in parsed.values() if p is not None]
            best = (min(means) if minimize else max(means)) if means else None
            cells = []
            for c in task_cols:
                p = parsed[c]
                if p is None:
                    cells.append("--")
                else:
                    mean, sem = p
                    if mean == best:
                        cells.append(f"$\\mathbf{{{mean:.2f}}}$")
                    else:
                        cells.append(f"${mean:.2f}$")
            label = task.replace("_", r"\_")
            if task == "average":
                print(r"\midrule")
                label = r"\textrm{Average}"
            print(label + " & " + " & ".join(cells) + r" \\")
        print(r"\bottomrule")
        print(r"\end{tabular}")
        print(r"\caption{" + caption + "}")
        print(r"\end{table*}")
    else:
        # methods are rows, tasks are columns
        label_cols = [c for c in ["workflow", "ptools", "model"] if c in df.columns]
        task_cols = [c for c in df.columns if c not in label_cols]

        # Build grouped two-line header
        _GROUP_NAMES = {
            "musr": "MuSR",
            "natplan": "NaturalPlan",
            "rulearena": "RuleArena",
        }
        groups = []  # list of (group_name, [col_names])
        for col in task_cols:
            if col == "average":
                groups.append((None, [col]))
            else:
                prefix = col.split("/")[0]
                if groups and groups[-1][0] == prefix:
                    groups[-1][1].append(col)
                else:
                    groups.append((prefix, [col]))

        _SUBTASK_NAMES = {"nba": "NBA"}

        def _subtask_label(col):
            if col == "average":
                return "Average"
            sub = col.split("/")[1]
            return _SUBTASK_NAMES.get(sub, sub.capitalize())

        n_task_cols = len(task_cols)
        print(r"\begin{table*}[ht]")
        print(r"\centering")
        print(r"\begin{tabular}{l" + "c" * n_task_cols + "}")
        print(r"\toprule")

        # First header line: group names with \multicolumn
        group_cells = [""]  # empty cell for the label column
        for prefix, cols in groups:
            n = len(cols)
            if prefix is None:
                group_cells.append(f"\\multicolumn{{{n}}}{{c}}{{}}")
            else:
                name = _GROUP_NAMES.get(prefix, prefix)
                group_cells.append(f"\\multicolumn{{{n}}}{{c}}{{{name}}}")
        print(" & ".join(group_cells) + r" \\")

        # Cmidrules for each group (skip ungrouped "average")
        col_idx = 2  # 1-indexed, column 1 is the label
        for prefix, cols in groups:
            n = len(cols)
            if prefix is not None:
                print(f"\\cmidrule(lr){{{col_idx}-{col_idx + n - 1}}}")
            col_idx += n

        # Second header line: subtask names
        subtask_cells = ["Workflow/Ptools"]
        for col in task_cols:
            subtask_cells.append(_subtask_label(col))
        print(" & ".join(subtask_cells) + r" \\")
        print(r"\midrule")

        # Find best per task column
        best_per_col = {}
        for col in task_cols:
            vals = [_parse_cell(v) for v in df[col]]
            means = [p[0] for p in vals if p is not None]
            if means:
                best_per_col[col] = min(means) if minimize else max(means)

        for _, row in df.iterrows():
            # Combined workflow/ptools label
            wf = str(row.get("workflow", ""))
            pt = str(row.get("ptools", row.get("toolkit", "")))
            label = f"{wf}/{pt}"
            cells = [label.replace("_", r"\_")]
            for c in task_cols:
                p = _parse_cell(row[c])
                if p is None:
                    cells.append("--")
                else:
                    mean, sem = p
                    if c in best_per_col and mean == best_per_col[c]:
                        cells.append(f"$\\mathbf{{{mean:.2f}}}$")
                    else:
                        cells.append(f"${mean:.2f}$")
            print(" & ".join(cells) + r" \\")
        print(r"\bottomrule")
        print(r"\end{tabular}")
        print(r"\caption{" + caption + "}")
        print(r"\end{table*}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-opus", action="store_true",
                        help="Include codedistill rows for model=opus")
    parser.add_argument("--suppress-tasks", nargs="+", default=[], metavar="TASK/SUBTASK",
                        help="Omit specified TASK/SUBTASK entries from the table")
    parser.add_argument("--suppress", nargs="+", default=[], metavar="WORKFLOW/PTOOLS",
                        help="Omit rows matching workflow/ptools (e.g. ReAct/human)")
    parser.add_argument("--transpose", action="store_true",
                        help="Show tasks as rows and methods as columns")
    parser.add_argument("--format", choices=["table", "latex-correct", "latex-cost"],
                        default="table", help="Output format")
    args = parser.parse_args()

    correct_df, cost_df = build_dataframes(
        include_opus=args.include_opus, suppress_tasks=args.suppress_tasks,
        suppress_rows=args.suppress, transpose=args.transpose)

    if args.format == "latex-correct":
        _print_latex(correct_df, "Correctness", minimize=False, transpose=args.transpose)
        return
    if args.format == "latex-cost":
        _print_latex(cost_df, "Cost (USD per 100 examples)", minimize=True, transpose=args.transpose)
        return

    print("=== Correctness ===")
    show_index = args.transpose
    print(correct_df.to_string(index=show_index))
    print()
    print("=== Cost (USD per 100 examples) ===")
    print(cost_df.to_string(index=show_index))


if __name__ == "__main__":
    main()
