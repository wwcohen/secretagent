#!/usr/bin/env python3
# /// script
# dependencies = ["pandas"]
# ///
"""Build tables of results of various learning/engineering/optimization methods."""

import os
import glob
import csv
import math

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


def read_correct_column(csv_path):
    """Read the 'correct' column from a results CSV, returning list of floats."""
    values = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row["correct"]
            if val in ("True", "true"):
                values.append(1.0)
            elif val in ("False", "false"):
                values.append(0.0)
            else:
                values.append(float(val))
    return values


def mean_sem(values):
    """Return (mean, standard error of mean) for a list of values."""
    n = len(values)
    if n == 0:
        return None, None
    mean = sum(values) / n
    if n == 1:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    sem = math.sqrt(variance / n)
    return mean, sem


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


def format_cell(mean, sem):
    """Format a mean +/- sem value for display."""
    if mean is None:
        return "—"
    return f"{mean:.3f}+/-{sem:.3f}"


def build_dataframe():
    """Build a DataFrame with methods as rows and tasks as columns."""
    col_names = [
        f"{t.split('/')[0].replace('natural_plan', 'natplan')}/{t.split('/')[1]}"
        for t in KEYTASKS
    ]
    rows = []

    # Row 1: engineered workflow
    row = {"Method": "engineered workflow"}
    for keytask, col in zip(KEYTASKS, col_names):
        task, subtask = keytask.split("/")
        csv_path = find_workflow_csv(task, subtask)
        if csv_path:
            values = read_correct_column(csv_path)
            m, s = mean_sem(values)
            row[col] = format_cell(m, s)
        else:
            row[col] = "—"
    rows.append(row)

    # Codedistill rows: learner_llm x ptool_class
    toolkit_labels = {"class2": "eng toolkit", "class3": "learned toolkit"}
    for learner_llm in ("opus", "gemini"):
        for ptool_class in ("class2", "class3"):
            toolfit = toolkit_labels[ptool_class]
            row = {"Method": f"codedist {learner_llm} {toolfit}"}
            for keytask, col in zip(KEYTASKS, col_names):
                task, subtask = keytask.split("/")
                csv_path = find_codedistill_csv(task, subtask, learner_llm=learner_llm, ptool_class=ptool_class)
                if csv_path:
                    values = read_correct_column(csv_path)
                    m, s = mean_sem(values)
                    row[col] = format_cell(m, s)
                else:
                    row[col] = "—"
            rows.append(row)

    return pd.DataFrame(rows)


def main():
    df = build_dataframe()
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
