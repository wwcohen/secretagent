"""Scan every val_results / val_results_full / results dir under benchmarks/
and produce a unified table:
  benchmark | label | n | acc | cost_total | model | path
"""
import json
import re
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path("/Users/yanjiarui/Desktop/Will_research/secretagent/benchmarks")

BENCHES = [
    "natural_plan", "musr", "finqa", "medcalc", "rulearena",
    "bbh/sports_understanding", "bbh/penguins_in_a_table",
    "bbh/geometric_shapes", "bbh/date_understanding",
    "tabmwp",
]

# Post-COMMON-reorg, the v4/v4g class1/class2 results live in:
#   benchmarks/COMMON/codedistill-ptools-results/<dst>/{val,test}_results_full/
#   benchmarks/COMMON/codedistill-workflow-results/<dst>/{val,test}_results_full/
# Mapping bench → dst (some bbh names get flattened to bbh_<sub>):
COMMON_BENCH_NAMES = {
    "natural_plan": "natural_plan",
    "musr": "musr",
    "finqa": "finqa",
    "medcalc": "medcalc",
    "rulearena": "rulearena",
    "tabmwp": "tabmwp",
    "bbh/sports_understanding":  "bbh_sports_understanding",
    "bbh/penguins_in_a_table":   "bbh_penguins_in_a_table",
    "bbh/geometric_shapes":      "bbh_geometric_shapes",
    "bbh/date_understanding":    "bbh_date_understanding",
}

records = []

def scan(bench, scope, base):
    base = ROOT / bench / base
    if not base.exists():
        return
    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        rcsv = d / "results.csv"
        rcfg = d / "config.yaml"
        if not rcsv.exists() or not rcfg.exists():
            continue
        try:
            df = pd.read_csv(rcsv)
            cfg = yaml.safe_load(rcfg.read_text()) or {}
        except Exception:
            continue
        # post-hoc paren-strip for BBH multiple-choice
        if 'bbh' in bench and 'predicted_output' in df.columns and 'expected_output' in df.columns:
            def norm(s):
                s = str(s).strip()
                if s.startswith('(') and s.endswith(')') and len(s) >= 3:
                    return s[1:-1].strip()
                return s
            df['correct_norm'] = df.apply(lambda r: norm(r['predicted_output']) == norm(r['expected_output']), axis=1)
            acc_val = float(df['correct_norm'].mean())
        else:
            acc_val = float(df['correct'].mean()) if 'correct' in df else None
        rec = {
            "bench": bench,
            "scope": scope,
            "name": d.name,
            "n": len(df),
            "acc": acc_val,
            "acc_raw": float(df["correct"].mean()) if "correct" in df else None,
            "cost": float(df["cost"].sum()) if "cost" in df else None,
            "model": (cfg.get("llm") or {}).get("model"),
            "split": (cfg.get("dataset") or {}).get("split"),
            "expt_name": (cfg.get("evaluate") or {}).get("expt_name"),
            "path": str(d),
        }
        records.append(rec)

for bench in BENCHES:
    for scope, base in [("val_full","val_results_full"),("val_mini","val_results"),("archived","results")]:
        # for results/, look at nested too
        if base == "results":
            res = ROOT / bench / "results"
            if res.exists():
                for d in sorted(res.iterdir()):
                    if d.is_dir():
                        rcsv = d / "results.csv"
                        if not rcsv.exists():
                            continue
                        try:
                            df = pd.read_csv(rcsv)
                            cfg = yaml.safe_load((d/"config.yaml").read_text()) or {} if (d/"config.yaml").exists() else {}
                        except Exception:
                            continue
                        # paren-strip for BBH archived too
                        if 'bbh' in bench and 'predicted_output' in df.columns and 'expected_output' in df.columns:
                            def normf(s):
                                s = str(s).strip()
                                if s.startswith('(') and s.endswith(')') and len(s) >= 3:
                                    return s[1:-1].strip()
                                return s
                            df['correct_norm'] = df.apply(lambda r: normf(r['predicted_output']) == normf(r['expected_output']), axis=1)
                            acc_val = float(df['correct_norm'].mean())
                        else:
                            acc_val = float(df['correct'].mean()) if 'correct' in df else None
                        records.append({
                            "bench": bench, "scope": "archived_inproject", "name": d.name,
                            "n": len(df), "acc": acc_val,
                            "cost": float(df["cost"].sum()) if "cost" in df else None,
                            "model": (cfg.get("llm") or {}).get("model"),
                            "split": (cfg.get("dataset") or {}).get("split"),
                            "expt_name": (cfg.get("evaluate") or {}).get("expt_name"),
                            "path": str(d),
                        })
            continue
        scan(bench, scope, base)

# Also scan COMMON/codedistill-{ptools,workflow}-results/<dst>/{val,test}_results_full/
def scan_common(bench, dst, common_subdir, scope_prefix):
    """bench is the canonical bench dir; common_subdir is the dirname under COMMON/."""
    base = ROOT / 'COMMON' / common_subdir / dst
    if not base.exists():
        return
    for results_kind in ['val_results_full', 'test_results_full']:
        sub = base / results_kind
        if not sub.exists():
            continue
        for d in sorted(sub.iterdir()):
            if not d.is_dir():
                continue
            rcsv = d / "results.csv"
            rcfg = d / "config.yaml"
            if not rcsv.exists() or not rcfg.exists():
                continue
            try:
                df = pd.read_csv(rcsv)
                cfg = yaml.safe_load(rcfg.read_text()) or {}
            except Exception:
                continue
            if 'bbh' in bench and 'predicted_output' in df.columns and 'expected_output' in df.columns:
                def norm(s):
                    s = str(s).strip()
                    if s.startswith('(') and s.endswith(')') and len(s) >= 3:
                        return s[1:-1].strip()
                    return s
                df['correct_norm'] = df.apply(lambda r: norm(r['predicted_output']) == norm(r['expected_output']), axis=1)
                acc_val = float(df['correct_norm'].mean())
            else:
                acc_val = float(df['correct'].mean()) if 'correct' in df else None
            records.append({
                "bench": bench,
                "scope": f"{scope_prefix}_{results_kind.replace('_full','')}",  # e.g. ptools_val_results / workflow_test_results
                "name": d.name,
                "n": len(df),
                "acc": acc_val,
                "acc_raw": float(df["correct"].mean()) if "correct" in df else None,
                "cost": float(df["cost"].sum()) if "cost" in df else None,
                "model": (cfg.get("llm") or {}).get("model"),
                "split": (cfg.get("dataset") or {}).get("split"),
                "expt_name": (cfg.get("evaluate") or {}).get("expt_name"),
                "path": str(d),
            })

for bench in BENCHES:
    dst = COMMON_BENCH_NAMES.get(bench)
    if dst is None: continue
    scan_common(bench, dst, 'codedistill-ptools-results', 'ptools')
    scan_common(bench, dst, 'codedistill-workflow-results', 'workflow')

df = pd.DataFrame(records)
print(f"Total rows: {len(df)}")
print(df.groupby(['bench','scope']).size().unstack(fill_value=0))
df.to_csv('/tmp/all_vals_scan.csv', index=False)
print("\nWrote /tmp/all_vals_scan.csv")
