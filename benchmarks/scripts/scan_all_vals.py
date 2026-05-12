"""Scan every val_results / val_results_full / results dir under benchmarks/
and produce a unified table:
  benchmark | label | n | acc | cost_total | model | path
"""
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

BENCHES = [
    "natural_plan", "musr", "finqa", "medcalc", "rulearena",
    "bbh/sports_understanding", "bbh/penguins_in_a_table",
    "bbh/geometric_shapes", "bbh/date_understanding",
    "tabmwp",
]

# Post-COMMON-reorg, the opus/gemini class1/class2 results live in:
#   paper/results/codedistill-ptools-results/<dst>/{val,test}_results_full/
#   paper/results/codedistill-workflow-results/<dst>/{val,test}_results_full/
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

MEDCALC_SUBSETS = {
    "formulas": {"dosage", "lab test", "physical"},
    "rules": {"diagnosis", "risk", "severity"},
}


def _bbh_acc(bench, df):
    if 'bbh' not in bench or not {'predicted_output', 'expected_output'} <= set(df.columns):
        return None

    def norm(s):
        s = str(s).strip()
        if s.startswith('(') and s.endswith(')') and len(s) >= 3:
            return s[1:-1].strip()
        return s

    return float(df.apply(lambda r: norm(r['predicted_output']) == norm(r['expected_output']), axis=1).mean())


def _append_record(bench, scope, name, df, cfg, path, subset=None,
                   sub_bench=None, missing_cost_as_zero=False):
    bbh_acc = _bbh_acc(bench, df)
    acc_val = bbh_acc if bbh_acc is not None else (float(df['correct'].mean()) if 'correct' in df else None)
    cost = float(df["cost"].sum()) if "cost" in df else (0.0 if missing_cost_as_zero else None)
    records.append({
        "bench": bench,
        "scope": scope,
        "name": name,
        "subset": subset,
        "sub_bench": sub_bench,
        "n": len(df),
        "acc": acc_val,
        "acc_raw": float(df["correct"].mean()) if "correct" in df else None,
        "cost": cost,
        "model": (cfg.get("llm") or {}).get("model"),
        "split": (cfg.get("dataset") or {}).get("split"),
        "expt_name": (cfg.get("evaluate") or {}).get("expt_name"),
        "path": str(path),
    })


def append_records(bench, scope, name, df, cfg, path, forced_sub_bench=None,
                   missing_cost_as_zero=False):
    """Append one scan row, except medcalc is always split into formulas/rules."""
    if bench == "medcalc" and "category" in df.columns:
        categories = df["category"].astype(str).str.lower()
        wrote_subset = False
        for subset, allowed in MEDCALC_SUBSETS.items():
            sub_df = df[categories.isin(allowed)]
            if sub_df.empty:
                continue
            _append_record(
                bench, scope, name, sub_df, cfg, path,
                subset=subset, sub_bench=f"medcalc_{subset}",
                missing_cost_as_zero=missing_cost_as_zero,
            )
            wrote_subset = True
        if wrote_subset:
            return
    _append_record(bench, scope, name, df, cfg, path,
                   sub_bench=forced_sub_bench,
                   missing_cost_as_zero=missing_cost_as_zero)


def sub_bench_from_run_name(bench, name):
    name = name.lower()
    if bench == "natural_plan":
        for sub in ("calendar", "meeting", "trip"):
            if f"natplan_{sub}" in name or sub in name:
                return f"natplan_{sub}"
    if bench == "musr":
        for sub in ("murder", "object", "team"):
            if f"musr_{sub}" in name or sub in name:
                return f"musr_{sub}"
    if bench == "rulearena":
        for sub in ("airline", "nba", "tax"):
            if f"rulearena_{sub}" in name or sub in name:
                return f"rulearena_{sub}"
    if bench == "medcalc":
        for subset in MEDCALC_SUBSETS:
            if f"medcalc_{subset}" in name:
                return f"medcalc_{subset}"
    return None


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
        append_records(bench, scope, d.name, df, cfg, d)

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
                        append_records(bench, "archived_inproject", d.name, df, cfg, d)
            continue
        scan(bench, scope, base)

# Also scan paper/results/codedistill-{ptools,workflow}-results/<dst>/{val,test}_results_full/
def scan_common(bench, dst, common_subdir, scope_prefix):
    """bench is the canonical bench dir; common_subdir is the dirname under paper/results/."""
    base = ROOT.parent / 'paper' / 'results' / common_subdir / dst
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
            append_records(
                bench,
                f"{scope_prefix}_{results_kind.replace('_full','')}",  # e.g. ptools_val_results / workflow_test_results
                d.name,
                df,
                cfg,
                d,
            )

for bench in BENCHES:
    dst = COMMON_BENCH_NAMES.get(bench)
    if dst is None: continue
    scan_common(bench, dst, 'codedistill-ptools-results', 'ptools')
    scan_common(bench, dst, 'codedistill-workflow-results', 'workflow')


def scan_orchestrator_common(bench, dst, common_subdir, scope):
    base = ROOT.parent / 'paper' / 'results' / common_subdir / dst / 'test_results_full'
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
        append_records(
            bench, scope, d.name, df, cfg, d,
            forced_sub_bench=sub_bench_from_run_name(bench, d.name),
            missing_cost_as_zero=True,
        )


for bench in BENCHES:
    dst = COMMON_BENCH_NAMES.get(bench)
    if dst is None:
        continue
    scan_orchestrator_common(bench, dst, 'orchestrator-results', 'orchestrator_test')
    scan_orchestrator_common(
        bench, dst, 'orchestrator-induced-ptools-results',
        'orchestrator_induced_test',
    )

df = pd.DataFrame(records)
print(f"Total rows: {len(df)}")
print(df.groupby(['bench','scope']).size().unstack(fill_value=0))
df.to_csv('/tmp/all_vals_scan.csv', index=False)
print("\nWrote /tmp/all_vals_scan.csv")
