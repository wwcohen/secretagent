# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "pyyaml"]
# ///
"""Exact NSGA-II evaluation counts for the rebuttal cost/effort table.

Derives, per benchmark, from the frozen paper artifacts in
benchmarks/COMMON/optimize-results/: how many candidate configs the
optimizer actually evaluated (rows in nsga2_summary.csv == subprocess
evaluations launched; duplicate chromosomes are EvalCache hits and never
re-run), whether the run was true NSGA-II or the exhaustive-enumeration
fallback (spaces <= 20 configs), pop size / generations, the validation
minibatch (dataset.n and split from the per-config config.yaml
snapshots), and the effective cases per evaluation (mode of distinct
case_name across snapshotted results.csv — catches e.g. NBA's 42-case
valid split vs the requested n=50).

Complements scripts/learning_costs.py, which sums the dollar costs but
left the eval-count multiplier as a hand-written "x 30-50" bound.

Usage:  uv run scripts/nsga2_eval_counts.py
"""

from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
OPT = ROOT / "benchmarks" / "COMMON" / "optimize-results"


def minibatch_info(bench_dir: Path):
    """(split, nominal n, effective cases/config, persisted case-rows, #dirs) from nsga_runs snapshots."""
    run_dirs = sorted(d for d in (bench_dir / "nsga_runs").glob("*") if d.is_dir()) if (bench_dir / "nsga_runs").exists() else []
    splits, ns, case_counts, total_rows = Counter(), Counter(), Counter(), 0
    for d in run_dirs:
        cfg_file = d / "config.yaml"
        if cfg_file.exists():
            ds = (yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}).get("dataset", {})
            splits[str(ds.get("split"))] += 1
            ns[ds.get("n")] += 1
        res_file = d / "results.csv"
        if res_file.exists():
            try:
                df = pd.read_csv(res_file)
                total_rows += len(df)
                if "case_name" in df.columns:
                    case_counts[df["case_name"].nunique()] += 1
            except Exception:
                pass
    mode = lambda c: c.most_common(1)[0][0] if c else None
    return mode(splits), mode(ns), mode(case_counts), total_rows, len(run_dirs)


def main():
    rows, totals = [], Counter()
    for bench_dir in sorted(p for p in OPT.iterdir() if p.is_dir() and not p.name.startswith("_")):
        summary_file = bench_dir / "nsga2_summary.csv"
        if not summary_file.exists():
            rows.append({"benchmark": bench_dir.name, "mode": "ARTIFACTS MISSING"})
            continue
        summary = pd.read_csv(summary_file)
        configs, valid = len(summary), int(summary["valid"].sum())

        gens = pd.read_csv(bench_dir / "nsga2_generations.csv")
        exhaustive = len(gens) == 1
        pop_gen = "exhaustive" if exhaustive else f"{int(gens.iloc[0]['new_evals'])}x{len(gens) - 1}"
        dup_hits = int(gens["cache_hits"].sum())
        if int(gens.iloc[-1]["total_evals"]) != configs:
            print(f"WARNING {bench_dir.name}: summary rows ({configs}) != generations total_evals "
                  f"({int(gens.iloc[-1]['total_evals'])})")

        split, n, eff, case_rows, n_dirs = minibatch_info(bench_dir)
        rows.append({
            "benchmark": bench_dir.name, "mode": "exhaustive" if exhaustive else "NSGA-II",
            "pop x gen": pop_gen, "configs": configs, "valid": valid, "dup hits": dup_hits,
            "split": split or "-", "n": n or "-", "eff. cases": eff or "-",
            "case-evals": configs * eff if eff else (configs * n if n else None),
            "snapshot rows": case_rows or "-", "dirs": n_dirs,
        })
        totals["configs"] += configs
        totals["nsga2" if not exhaustive else "exhaustive"] += configs
        if eff:
            totals["case_evals"] += configs * eff

    cols = ["benchmark", "mode", "pop x gen", "configs", "valid", "dup hits",
            "split", "n", "eff. cases", "case-evals", "snapshot rows", "dirs"]
    print("| " + " | ".join(cols) + " |")
    print("|" + "|".join("---" for _ in cols) + "|")
    for r in rows:
        print("| " + " | ".join(str(r.get(c, "-")) for c in cols) + " |")

    print(f"\nTotal configs evaluated: {totals['configs']} "
          f"({totals['nsga2']} true NSGA-II + {totals['exhaustive']} exhaustive enumeration)")
    print(f"Total case-evaluations (configs x effective cases, where snapshots exist): {totals['case_evals']}")

    print("""
Notes for the rebuttal text:
 - 'configs' = rows in nsga2_summary.csv = evaluations actually launched; EvalCache
   dedups repeated chromosomes ('dup hits' = generation-log cache_hits, never re-run).
 - natplan meeting/trip used the exhaustive fallback (search space <= 20 configs),
   not NSGA-II; their single generation row is synthetic (elapsed_s=0).
 - sports_understanding has no per-config snapshots in COMMON; its minibatch was
   dataset.split=valid dataset.n=50 per the archived EXPERIMENT_CMDS.md (Phase 1).
 - medcalc: a sweep ran (test_pass_summary.csv residue) but nsga2_summary.csv was
   never committed -> config count unrecoverable; do not cite one.
 - rulearena airline/tax are registered spaces with no artifacts -> never run.
 - musr_murder's minibatch split is murder_mysteries_test (visible above): its
   Pareto selection used the test split, as its REPRODUCE.md discloses.
 - Per-evaluation LLM *call* counts were not persisted. Dollar costs are summable
   from nsga_runs/*/results.csv where snapshotted; rulearena_nba additionally has
   a complete fresh-vs-uncached accounting in rulearena_nba/CACHE_FINDINGS.md.
 - 'snapshot rows' counts all persisted results.csv rows, which include
   sub-interface logging rows for react/pot configs (why it can exceed case-evals).""")


if __name__ == "__main__":
    main()
