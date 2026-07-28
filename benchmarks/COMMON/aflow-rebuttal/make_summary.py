# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "tabulate"]
# ///
"""Regenerate the AFlow rebuttal results table from collected artifacts.

Reads (all produced by collect.sh + the secretagent reference-cell runs):
  - results/<bench>/workspace/workflows/results.json  -> per-round validation means
  - results/test_logs/<Dataset>/round_N/*.csv         -> held-out test score/cost
  - results/<bench>/*.log.gz                          -> search cost accounting
      executor share = sum of results.json total_cost; optimizer share =
      (sum of all "Cost: $" lines in the log) - executor share.
  - ../../bbh/sports_understanding/results/*.gemlite_* and
    ../../finqa/results/*.gemlite_*                   -> reference cells (same
      executor model, same splits), read from each run dir's results.csv.

Usage:  uv run benchmarks/COMMON/aflow-rebuttal/make_summary.py [--format latex]
"""

import argparse
import glob
import gzip
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BENCHES = {"sports": "SportsUnderstanding", "finqa": "FinQA"}


def val_rounds(bench: str):
    f = HERE / "results" / bench / "workspace" / "workflows" / "results.json"
    if not f.exists():
        return None
    entries = json.loads(f.read_text(encoding="utf-8"))
    by = defaultdict(list)
    for e in entries:
        by[e["round"]].append(e)
    means = {r: sum(x["score"] for x in v) / len(v) for r, v in by.items()}
    best = max(sorted(means), key=lambda r: means[r])
    executor_cost = sum(x["total_cost"] for x in entries)
    return {"means": means, "best": best, "best_val": means[best],
            "rounds": len(means), "evals": len(entries), "executor_cost": executor_cost}


def test_result(dataset: str):
    pats = sorted(glob.glob(str(HERE / "results" / "test_logs" / dataset / "round_*" / "*.csv")))
    if not pats:
        return None
    df = pd.read_csv(pats[-1])
    rnd = re.search(r"round_(\d+)", pats[-1]).group(1)
    return {"round": int(rnd), "score": df["score"].mean(), "n": len(df),
            "cost_per_case": df["cost"].max() / len(df)}


def search_costs(bench: str):
    """{'final': $ in the paper-facing search log, 'all_attempts': $ across all
    archived attempt logs incl. failed ones}. 'Cost: $' lines cover both executor
    and optimizer calls (optimizer thinking tokens under-counted; see README)."""
    final_names = {"sports": "sports_search.log.gz", "finqa": "finqa_search.log.gz"}
    out = {"final": 0.0, "all_attempts": 0.0}
    for lg in glob.glob(str(HERE / "results" / bench / "*.log.gz")):
        sub = 0.0
        with gzip.open(lg, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r"Cost: \$([0-9.]+) ", line)
                if m:
                    sub += float(m.group(1))
        out["all_attempts"] += sub
        if os.path.basename(lg) == final_names.get(bench):
            out["final"] += sub
    return out


def candidate_audit(bench: str, dataset: str):
    """Per-candidate held-out audit: every searched round scored once on the
    test split with token/call accounting (usage.json written by test_pass.py)."""
    v = val_rounds(bench)
    rows = []
    for uj in sorted(glob.glob(str(HERE / "results" / "test_logs" / dataset / "round_*" / "usage.json"))):
        u = json.loads(Path(uj).read_text(encoding="utf-8"))
        rows.append({"round": u["round"],
                     "val": round(v["means"].get(u["round"], float("nan")), 3) if v else None,
                     "test": round(u["score"], 3),
                     "cost_per_case": round(u["cost_per_case"], 7),
                     "calls_per_case": round(u["calls_per_case"], 2),
                     "out_tok_per_case": round(u["out_tok_per_case"], 1)})
    return pd.DataFrame(rows).sort_values("round") if rows else pd.DataFrame()


def reference_cells():
    """gemlite_* run dirs in the two benchmarks' results/ (created by
    scripts/run_gemlite_reference_cells.sh)."""
    roots = {
        "sports": HERE.parents[1] / "bbh" / "sports_understanding" / "results",
        "finqa": HERE.parents[1] / "finqa" / "results",
    }
    rows = []
    for bench, root in roots.items():
        for d in sorted(glob.glob(str(root / "*.gemlite_*"))):
            csv = os.path.join(d, "results.csv")
            if not os.path.exists(csv) or "_smoke" in d:
                continue
            df = pd.read_csv(csv)
            scored = df[df["correct"].notna()]
            m = re.search(r"gemlite_(\w+?)_(valid|test)(\d+)", d)
            if not m:
                continue
            rows.append({"bench": bench, "method": m.group(1), "split": m.group(2),
                         "n": int(m.group(3)), "correct": scored["correct"].mean(),
                         "cost": df["cost"].sum()})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["markdown", "latex"], default="markdown")
    args = ap.parse_args()

    lines = []
    for bench, dataset in BENCHES.items():
        v = val_rounds(bench)
        t = test_result(dataset)
        c = search_costs(bench)
        if not v:
            lines.append({"bench": bench, "note": "no search artifacts yet"})
            continue
        lines.append({
            "bench": bench, "rounds": v["rounds"], "cand_evals": v["evals"],
            "best_round": v["best"], "best_val": round(v["best_val"], 4),
            "test": round(t["score"], 4) if t else None,
            "test_n": t["n"] if t else None,
            "test_cost_per_case": round(t["cost_per_case"], 6) if t else None,
            "search_cost": round(c["final"], 4),
            "search_exec_cost": round(v["executor_cost"], 4),
            "search_opt_cost_est": round(c["final"] - v["executor_cost"], 4),
            "search_cost_incl_failed_attempts": round(c["all_attempts"], 4),
        })
    aflow = pd.DataFrame(lines)
    refs = reference_cells()

    if args.format == "latex":
        esc = lambda s: str(s).replace("_", r"\_")
        print("% AFlow arm")
        print(aflow.to_string(index=False))
        print("% Reference cells (gemini-2.5-flash-lite, secretagent harness)")
        if len(refs):
            piv = refs.pivot_table(index=["bench", "split", "n"], columns="method",
                                   values="correct")
            print(piv.round(3).to_string())
        return

    print("## AFlow arm (executor gemini-2.5-flash-lite, optimizer gemini-3.1-pro-preview)")
    print(aflow.to_markdown(index=False) if hasattr(aflow, "to_markdown") else aflow.to_string(index=False))
    print("\n## Reference cells (same executor, secretagent harness)")
    if len(refs):
        print(refs.round(4).to_markdown(index=False))
    else:
        print("(none found yet — run scripts/run_gemlite_reference_cells.sh)")

    audit = candidate_audit("sports", "SportsUnderstanding")
    if len(audit) > 1:
        print("\n## AFlow candidate audit — every searched Sports round on held-out test")
        print(audit.to_markdown(index=False))


if __name__ == "__main__":
    main()
