#!/usr/bin/env python3
# /// script
# dependencies = ["pandas"]
# ///
"""Aggregate learning/optimization-phase costs recorded in the repo.

Stages:
  A. Orchestration learning: results/orchestration_learner/*/report.json -> total_supervisor_cost
  B. NSGA-II search: COMMON/optimize-results/*/nsga2_summary.csv -> per-config eval cost columns
  C. Code distillation + ptool induction: savefile dirs (report any cost fields found in json)

Usage:  uv run scripts/learning_costs.py
"""

import glob
import json
import os

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(REPO, "benchmarks")

print("== A. Orchestration learner supervisor costs ==")
rows = []
for rp in sorted(glob.glob(os.path.join(BENCH, "**/orchestration_learner/*/report.json"), recursive=True)):
    try:
        r = json.load(open(rp))
    except Exception:
        continue
    rel = os.path.relpath(rp, BENCH)
    rows.append({
        "run": rel.replace("/report.json", ""),
        "supervisor_cost": r.get("total_supervisor_cost"),
        "iters": len(r.get("iterations", [])),
        "best_train_acc": r.get("best_train_accuracy"),
        "final_eval_acc": r.get("final_eval_accuracy"),
    })
df = pd.DataFrame(rows)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 110)
print(df.to_string(index=False))
print(f"TOTAL supervisor cost across {len(df)} orch runs: ${df['supervisor_cost'].sum():.2f}")

print()
print("== B. NSGA-II summaries ==")
import numpy as np  # noqa: E402
tot = 0.0
for csvp in sorted(glob.glob(os.path.join(BENCH, "COMMON/optimize-results/*/nsga2_summary.csv"))):
    d = pd.read_csv(csvp)
    name = os.path.basename(os.path.dirname(csvp))
    if "cost" not in d.columns:
        print(f"{name}: {len(d)} configs, no cost column")
        continue
    fin = d.loc[np.isfinite(d["cost"]), "cost"]
    tot += fin.sum()
    print(f"{name}: {len(d)} configs ({len(fin)} finite-cost), sum(mean-cost/example) = {fin.sum():.3f}")
print(f"TOTAL sum(mean-cost/example over configs) = {tot:.3f}; x val-minibatch size (~30-50) bounds search eval cost")

print()
print("== C. cost fields in distill/induction savefiles ==")
hits = 0
for pat in ("COMMON/codedistill-workflow-results/**/*.json", "COMMON/codedistill-ptools-results/**/*.json",
            "*/learned*/**/*.json", "*/learned*/*.json"):
    for jp in glob.glob(os.path.join(BENCH, pat), recursive=True):
        try:
            txt = open(jp).read()
        except Exception:
            continue
        if '"cost' in txt or "supervisor_cost" in txt or "total_cost" in txt:
            try:
                j = json.load(open(jp))
            except Exception:
                continue

            def find_costs(d, pfx=""):
                out = []
                if isinstance(d, dict):
                    for k, v in d.items():
                        if "cost" in str(k).lower() and isinstance(v, (int, float)):
                            out.append((pfx + str(k), v))
                        elif isinstance(v, dict):
                            out.extend(find_costs(v, pfx + str(k) + "."))
                return out

            found = find_costs(j)
            if found:
                hits += 1
                print(os.path.relpath(jp, BENCH), found[:4])
if hits == 0:
    print("(no explicit cost fields found in distill/induction savefiles)")
print()
print("NOTE: run_summary.json total_cost_usd in codedistill result dirs records DEPLOYMENT eval cost")
print("(often ~$0 because distilled code makes no LLM calls), not the learner's own calls. The")
print("distillation/induction learner-side cost is not persisted per-run — recording gap.")
