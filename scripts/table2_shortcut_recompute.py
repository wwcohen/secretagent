#!/usr/bin/env python3
# /// script
# dependencies = ["pandas"]
# ///
"""Recompute Table 2 aggregates with the 3 shortcut-solvable benchmarks
(natplan/meeting, natplan/trip, rulearena/nba) removed, for every row
(engineered and learned arms alike).

Reuses scripts/learning_table.py finders; fills the cells that script misses
(medcalc columns, orchestrator legacy-layout rows) from the exact dirs named
in learning_tables_notes.txt and orchestrator-results/README.md. Prints every
cell's source dir as an audit trail.

Usage:  uv run scripts/table2_shortcut_recompute.py
"""

import os
import sys
import glob

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import learning_table as lt  # noqa: E402

COMMON = os.path.join(REPO, "benchmarks", "COMMON")

TASKS = [
    "musr/murder",
    "musr/object",
    "musr/team",
    "natural_plan/meeting",
    "natural_plan/trip",
    "rulearena/nba",
    "medcalc/formulas",
    "medcalc/rules",
]
BYPASS = {"natural_plan/meeting", "natural_plan/trip", "rulearena/nba"}

# sub_bench naming used by the legacy orchestrator layout
LEGACY_NAME = {
    "musr/murder": "musr_murder",
    "musr/object": "musr_object",
    "musr/team": "musr_team",
    "natural_plan/meeting": "natplan_meeting",
    "natural_plan/trip": "natplan_trip",
    "rulearena/nba": "rulearena_nba",
    "medcalc/formulas": "medcalc_formulas",
    "medcalc/rules": "medcalc_rules",
}

# Explicit medcalc cell dirs from learning_tables_notes.txt
MEDCALC = {
    ("human/human", "medcalc/formulas"): "results/medcalc/formulas/20260425.233811.workflow",
    ("human/human", "medcalc/rules"): "results/medcalc/rules/20260425.233811.workflow",
    ("ReAct/human", "medcalc/formulas"): "results/medcalc/formulas/20260426.004308.react",
    ("ReAct/human", "medcalc/rules"): "results/medcalc/rules/20260426.004308.react",
    ("ReAct/learned", "medcalc/formulas"): "learner-results/medcalc/formulas/20260504.143154.react_induced_state_oc1_mp5",
    ("ReAct/learned", "medcalc/rules"): "learner-results/medcalc/rules/20260504.143154.react_induced_state_oc1_mp5",
    ("codedist/human", "medcalc/formulas"): "codedist-formulas-c2",
    ("codedist/human", "medcalc/rules"): "codedist-rules-c2",
    ("codedist/learned", "medcalc/formulas"): "codedist-formulas-c3",
    ("codedist/learned", "medcalc/rules"): "codedist-rules-c3",
    ("orch-wfseed/human", "medcalc/formulas"): "orchestrator-results/existing_workflow/medcalc_formulas/results/20260504.025838.test_deepseek_v3_1",
    ("orch-wfseed/human", "medcalc/rules"): "orchestrator-results/existing_workflow/medcalc_rules/results/20260504.025838.test_deepseek_v3_1",
    ("orch-toolseed/human", "medcalc/formulas"): "orchestrator-results/seed_from_ptools/medcalc_formulas/results/20260504.084524.test_deepseek_v3_1",
    ("orch-toolseed/human", "medcalc/rules"): "orchestrator-results/seed_from_ptools/medcalc_rules/results/20260504.084524.test_deepseek_v3_1",
}
CODEDISTILL_MEDCALC = {
    "codedist-formulas-c2": "codedistill-workflow-results/medcalc/test_results_full/formulas/20260502.043152.medcalc_test_full_class2_gemini_cache",
    "codedist-rules-c2": "codedistill-workflow-results/medcalc/test_results_full/rules/20260502.043152.medcalc_test_full_class2_gemini_cache",
    "codedist-formulas-c3": "codedistill-workflow-results/medcalc/test_results_full/formulas/20260507.050302.medcalc_test_full_class3_gemini_cache",
    "codedist-rules-c3": "codedistill-workflow-results/medcalc/test_results_full/rules/20260507.050302.medcalc_test_full_class3_gemini_cache",
}


def medcalc_csv(row_label, keytask):
    key = (row_label, keytask)
    if key not in MEDCALC:
        return None
    rel = MEDCALC[key]
    rel = CODEDISTILL_MEDCALC.get(rel, rel)
    path = os.path.join(COMMON, rel, "results.csv")
    return path if os.path.isfile(path) else None


def orchestrator_legacy_csv(condition, keytask):
    """condition: existing_workflow | seed_from_ptools; latest run under results/."""
    sub = LEGACY_NAME[keytask]
    pattern = os.path.join(COMMON, "orchestrator-results", condition, sub, "results", "*")
    matches = sorted(d for d in glob.glob(pattern) if os.path.isfile(os.path.join(d, "results.csv")))
    return os.path.join(matches[-1], "results.csv") if matches else None


def cell(csv_path):
    if not csv_path:
        return None
    df = lt.read_csv(csv_path)
    return df


ROWS = [
    ("human/human", lambda t, s: lt.find_workflow_csv(t, s)),
    ("ReAct/human", lambda t, s: lt.find_react_csv(t, s)),
    ("ReAct/learned", lambda t, s: lt.find_react_learned_csv(t, s)),
    ("codedist/human", lambda t, s: lt.find_codedistill_csv(t, s, learner_llm="gemini", ptool_class="class2")),
    ("codedist/learned", lambda t, s: lt.find_codedistill_csv(t, s, learner_llm="gemini", ptool_class="class3")),
    ("orch-wfseed/human", lambda t, s: None),
    ("orch-toolseed/human", lambda t, s: None),
    ("orch/learned", lambda t, s: lt.find_orchestrator_learned_csv(t, s)),
    ("nsga/auto", lambda t, s: lt.find_optimizer_csv(t, s)),
]
ORCH_LEGACY = {"orch-wfseed/human": "existing_workflow", "orch-toolseed/human": "seed_from_ptools"}


def find_cell_csv(label, finder, keytask):
    task, subtask = keytask.split("/")
    if keytask.startswith("medcalc/"):
        return medcalc_csv(label, keytask)
    if label in ORCH_LEGACY:
        return orchestrator_legacy_csv(ORCH_LEGACY[label], keytask)
    if label == "orch/learned":
        p = finder(task, subtask)
        if p is None:
            sub = LEGACY_NAME[keytask]
            pattern = os.path.join(COMMON, "orchestrator-induced-ptools-results", "**", f"*{subtask}*", "results.csv")
            matches = sorted(glob.glob(pattern, recursive=True))
            return matches[-1] if matches else None
        return p
    return finder(task, subtask)


def main():
    acc = {}
    cost = {}
    npts = {}
    paths = {}
    for label, finder in ROWS:
        for keytask in TASKS:
            csv_path = find_cell_csv(label, finder, keytask)
            paths[(label, keytask)] = csv_path
            df = cell(csv_path)
            if df is None:
                continue
            acc[(label, keytask)] = df["correct"].mean()
            npts[(label, keytask)] = len(df)
            if "cost" in df.columns:
                cost[(label, keytask)] = df["cost"].mean() * 100

    col_short = {t: t.replace("natural_plan", "natplan") for t in TASKS}

    def grid(d, fmt):
        rows = []
        for label, _ in ROWS:
            row = {"row": label}
            for t in TASKS:
                v = d.get((label, t))
                row[col_short[t]] = fmt(v) if v is not None else "—"
            rows.append(row)
        return pd.DataFrame(rows)

    def averages(d):
        out = []
        for label, _ in ROWS:
            all_vals = [d[(label, t)] for t in TASKS if (label, t) in d]
            keep_vals = [d[(label, t)] for t in TASKS if (label, t) in d and t not in BYPASS]
            byp_vals = [d[(label, t)] for t in TASKS if (label, t) in d and t in BYPASS]
            out.append({
                "row": label,
                "avg_all(n)": f"{sum(all_vals)/len(all_vals):.3f} ({len(all_vals)})" if all_vals else "—",
                "avg_excl_bypass(n)": f"{sum(keep_vals)/len(keep_vals):.3f} ({len(keep_vals)})" if keep_vals else "—",
                "avg_bypass_only(n)": f"{sum(byp_vals)/len(byp_vals):.3f} ({len(byp_vals)})" if byp_vals else "—",
                "delta": f"{sum(keep_vals)/len(keep_vals) - sum(all_vals)/len(all_vals):+.3f}" if all_vals and keep_vals else "—",
            })
        return pd.DataFrame(out)

    pd.set_option("display.width", 250)
    print("=== Accuracy grid (test) ===")
    print(grid(acc, lambda v: f"{v:.2f}").to_string(index=False))
    print()
    print("=== Accuracy averages: all 8 cols vs excluding natplan_meeting/trip + nba ===")
    print(averages(acc).to_string(index=False))
    print()
    print("=== Cost averages (USD/100 ex): same treatment ===")
    print(averages(cost).to_string(index=False))
    print()
    print("=== N per cell ===")
    print(grid(npts, lambda v: str(int(v))).to_string(index=False))
    print()
    print("=== Cell -> results dir (audit trail) ===")
    for (label, t), p in paths.items():
        if p:
            print(f"{label:22s} {col_short[t]:18s} {os.path.relpath(p, COMMON)}")
        else:
            print(f"{label:22s} {col_short[t]:18s} MISSING")


if __name__ == "__main__":
    main()
