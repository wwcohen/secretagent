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
    result = find_latest_dir(subtask_dir, "*.react")
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


def format_cell(series):
    """Format mean +/- sem from a pandas Series."""
    if series is None or series.empty:
        return "—"
    m = series.mean()
    s = series.sem()
    return f"{m:.2f}+/-{s:.2f}"


def _add_row(correct_rows, cost_rows, label_cols, col_names, find_fn):
    """Add a row to both correct and cost tables using find_fn to locate CSVs."""
    correct_row = dict(label_cols)
    cost_row = dict(label_cols)
    for keytask, col in zip(KEYTASKS, col_names):
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


def build_dataframes(include_opus=False):
    """Build DataFrames for correctness and cost (USD per 100 examples)."""
    col_names = [
        f"{t.split('/')[0].replace('natural_plan', 'natplan')}/{t.split('/')[1]}"
        for t in KEYTASKS
    ]
    correct_rows = []
    cost_rows = []

    # Row 1: engineered workflow
    _add_row(correct_rows, cost_rows,
             {"workflow": "human", "model": "-", "toolkit": "human"},
             col_names, find_workflow_csv)

    # Row 2: ReAct with human toolkit
    _add_row(correct_rows, cost_rows,
             {"workflow": "ReAct", "model": "-", "toolkit": "human"},
             col_names, find_react_csv)

    # Row 3: ReAct / Deepseek-V3 / learned
    _add_row(correct_rows, cost_rows,
             {"workflow": "ReAct", "model": "Deepseek-V3", "toolkit": "learned"},
             col_names, find_react_learned_csv)

    # Codedistill rows: learner_llm x ptool_class
    toolkit_labels = {"class2": "human", "class3": "learned"}
    learner_llms = ("opus", "gemini") if include_opus else ("gemini",)
    for learner_llm in learner_llms:
        for ptool_class in ("class2", "class3"):
            label = {"workflow": "codedist", "model": learner_llm, "toolkit": toolkit_labels[ptool_class]}
            _add_row(correct_rows, cost_rows, label, col_names,
                     lambda t, s, ll=learner_llm, pc=ptool_class: find_codedistill_csv(t, s, learner_llm=ll, ptool_class=pc))

    correct_df = pd.DataFrame(correct_rows)
    cost_df = pd.DataFrame(cost_rows)

    # Create method label as index, transpose so tasks are rows
    label_cols = ["workflow", "model", "toolkit"]
    for df in (correct_df, cost_df):
        if include_opus:
            df.index = df.apply(lambda r: f"{r['workflow']}/{r['model']}/{r['toolkit']}", axis=1)
        else:
            df.index = df.apply(lambda r: f"{r['workflow']}/{r['toolkit']}", axis=1)
        df.drop(columns=label_cols, inplace=True)

    correct_df = correct_df.T
    cost_df = cost_df.T

    # Add average row over task rows
    for df in (correct_df, cost_df):
        avgs = {}
        for col in df.columns:
            vals = []
            for cell in df[col]:
                if isinstance(cell, str) and "+/-" in cell:
                    vals.append(float(cell.split("+/-")[0]))
            if vals:
                avgs[col] = f"{sum(vals)/len(vals):.2f}"
            else:
                avgs[col] = "—"
        df.loc["average"] = avgs

    return correct_df, cost_df


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-opus", action="store_true",
                        help="Include codedistill rows for model=opus")
    args = parser.parse_args()

    correct_df, cost_df = build_dataframes(include_opus=args.include_opus)
    print("=== Correctness ===")
    print(correct_df.to_string())
    print()
    print("=== Cost (USD per 100 examples) ===")
    print(cost_df.to_string())


if __name__ == "__main__":
    main()
