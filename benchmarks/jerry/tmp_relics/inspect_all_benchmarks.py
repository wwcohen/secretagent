"""Comprehensive per-benchmark inspection.

For each of our 16 sub-benchmarks, report:
  - Data: train/valid/test sizes
  - Conf files (which workflow.yaml etc.)
  - Recordings: train_full + val_baseline_full done?
  - Class 1/2/3 v4 distill outputs?
  - Class 1/2/3 v4 vals done?
  - Misc issues (FHIR-required, agent-only, etc.)
"""
import json
from pathlib import Path
import yaml

ROOT = Path("/Users/yanjiarui/Desktop/Will_research/secretagent/benchmarks")

# (sub_bench_label, bench_dir, sub_specific_check_str)
BENCHES = [
    ("natplan_calendar",   "natural_plan", "calendar"),
    ("natplan_meeting",    "natural_plan", "meeting"),
    ("natplan_trip",       "natural_plan", "trip"),
    ("musr_murder",        "musr",         "murder"),
    ("musr_object",        "musr",         "object"),
    ("musr_team",          "musr",         "team"),
    ("bbh_sports",         "bbh/sports_understanding", None),
    ("bbh_penguins",       "bbh/penguins_in_a_table",  None),
    ("bbh_geometric",      "bbh/geometric_shapes",     None),
    ("bbh_date",           "bbh/date_understanding",   None),
    ("medcalc",            "medcalc",                  None),
    ("finqa",              "finqa",                    None),
    ("rulearena_airline",  "rulearena",  "airline"),
    ("rulearena_nba",      "rulearena",  "nba"),
    ("rulearena_tax",      "rulearena",  "tax"),
    ("tabmwp",             "tabmwp",     None),
]

def count_lines(p):
    if not p.exists(): return None
    try:
        with p.open() as f:
            return sum(1 for _ in f)
    except Exception:
        return None

def first_match(dir_, *patterns):
    if not dir_.exists(): return []
    found = []
    for p in patterns:
        for f in dir_.glob(p):
            found.append(f.name)
    return found

def check_dir_for_sub(d, sub):
    if not d.exists(): return []
    if sub is None:
        return [x.name for x in sorted(d.iterdir()) if x.is_dir()]
    return [x.name for x in sorted(d.iterdir()) if x.is_dir() and sub in x.name.lower()]

print(f"{'sub_bench':<22} | {'rec_train':<5} | {'rec_react':<5} | {'val_baseline':<12} | {'c1v4':<6} | {'c2v4':<6} | {'c3v4':<6} | issues")
print("-" * 120)

for label, bench_dir, sub in BENCHES:
    bench = ROOT / bench_dir
    if not bench.exists():
        print(f"{label:<22} | DIR MISSING")
        continue

    # recordings
    rec_train = check_dir_for_sub(bench / "recordings_full", sub)
    rec_train = [x for x in rec_train if "react" not in x.lower()]
    rec_react = check_dir_for_sub(bench / "recordings_full", sub)
    rec_react = [x for x in rec_react if "react" in x.lower()]

    # val baseline
    val_baseline = check_dir_for_sub(bench / "val_results_full", sub)
    val_baseline = [x for x in val_baseline if "baseline" in x.lower()]

    # learned dirs (class 1 v4 = codedistill_config.yaml; class 2/3 v4 = workflow_distill subdirs)
    c1v4_cfg = bench / "learned_v4" / "codedistill_config.yaml"
    if c1v4_cfg.exists():
        n_enabled = len(yaml.safe_load(c1v4_cfg.read_text()).get('ptools', {}) or {})
        c1v4_status = f"{n_enabled} EN"
    else:
        # See if learned_v4 dir exists with any ptool subdirs
        if (bench / "learned_v4").exists():
            n_subdirs = sum(1 for x in (bench / "learned_v4").iterdir() if x.is_dir())
            c1v4_status = f"0 EN ({n_subdirs}d)" if n_subdirs > 0 else "no dist"
        else:
            c1v4_status = "no dir"

    c2v4_dirs = check_dir_for_sub(bench / "learned_class2_v4", sub)
    c2v4_dirs = [x for x in c2v4_dirs if 'workflow_distill' in x]
    c2v4_status = f"{len(c2v4_dirs)} dist" if c2v4_dirs else "no"

    c3v4_dirs = check_dir_for_sub(bench / "learned_class3_v4", sub)
    c3v4_dirs = [x for x in c3v4_dirs if 'workflow_distill' in x]
    c3v4_status = f"{len(c3v4_dirs)} dist" if c3v4_dirs else "no"

    # vals for c1/c2/c3
    val_c1 = check_dir_for_sub(bench / "val_results_full", sub)
    val_c1 = [x for x in val_c1 if 'class1v4' in x.lower()]
    val_c2 = check_dir_for_sub(bench / "val_results_full", sub)
    val_c2 = [x for x in val_c2 if 'class2v4' in x.lower()]
    val_c3 = check_dir_for_sub(bench / "val_results_full", sub)
    val_c3 = [x for x in val_c3 if 'class3v4' in x.lower()]

    issues = []
    if not rec_train: issues.append("no train_rec")
    if not val_baseline: issues.append("no val_baseline")
    if "no dir" in c1v4_status or "no dist" in c1v4_status: issues.append("c1v4 missing")
    if not c2v4_dirs: issues.append("c2v4 missing")
    if not val_c2 and c2v4_dirs: issues.append("c2v4 val pending")
    if c3v4_dirs and not val_c3: issues.append("c3v4 val pending")
    if not c3v4_dirs: pass  # not all need c3

    rec_t = "✓" if rec_train else "✗"
    rec_r = "✓" if rec_react else "✗"
    vb = "✓"+f"({len(val_baseline)})" if val_baseline else "✗"
    c1 = c1v4_status[:6]
    c2 = (f"d{len(c2v4_dirs)}+v{len(val_c2)}" if c2v4_dirs else "✗")[:6]
    c3 = (f"d{len(c3v4_dirs)}+v{len(val_c3)}" if c3v4_dirs else "✗")[:6]

    print(f"{label:<22} | {rec_t:<5} | {rec_r:<5} | {vb:<12} | {c1:<6} | {c2:<6} | {c3:<6} | {', '.join(issues)}")
