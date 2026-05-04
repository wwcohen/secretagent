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


def read_correct_series(csv_path):
    """Read the 'correct' column from a results CSV as a numeric pandas Series."""
    df = pd.read_csv(csv_path)
    col = df["correct"]
    # Handle True/False strings
    if col.dtype == object:
        col = col.map({"True": 1.0, "true": 1.0, "False": 0.0, "false": 0.0})
    return col.astype(float)


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


def build_dataframe():
    """Build a DataFrame with methods as rows and tasks as columns."""
    col_names = [
        f"{t.split('/')[0].replace('natural_plan', 'natplan')}/{t.split('/')[1]}"
        for t in KEYTASKS
    ]
    rows = []

    # Row 1: engineered workflow
    row = {"workflow": "human", "model": "-", "toolkit": "human"}
    for keytask, col in zip(KEYTASKS, col_names):
        task, subtask = keytask.split("/")
        csv_path = find_workflow_csv(task, subtask)
        if csv_path:
            row[col] = format_cell(read_correct_series(csv_path))
        else:
            row[col] = "—"
    rows.append(row)

    # Codedistill rows: learner_llm x ptool_class
    toolkit_labels = {"class2": "human", "class3": "learned"}
    for learner_llm in ("opus", "gemini"):
        for ptool_class in ("class2", "class3"):
            row = {"workflow": "codedist", "model": learner_llm, "toolkit": toolkit_labels[ptool_class]}
            for keytask, col in zip(KEYTASKS, col_names):
                task, subtask = keytask.split("/")
                csv_path = find_codedistill_csv(task, subtask, learner_llm=learner_llm, ptool_class=ptool_class)
                if csv_path:
                    row[col] = format_cell(read_correct_series(csv_path))
                else:
                    row[col] = "—"
            rows.append(row)

    # Row: ReAct / Deepseek-V3 / learned
    row = {"workflow": "ReAct", "model": "Deepseek-V3", "toolkit": "learned"}
    for keytask, col in zip(KEYTASKS, col_names):
        task, subtask = keytask.split("/")
        csv_path = find_react_learned_csv(task, subtask)
        if csv_path:
            row[col] = format_cell(read_correct_series(csv_path))
        else:
            row[col] = "—"
    rows.append(row)

    return pd.DataFrame(rows)


def main():
    df = build_dataframe()
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
