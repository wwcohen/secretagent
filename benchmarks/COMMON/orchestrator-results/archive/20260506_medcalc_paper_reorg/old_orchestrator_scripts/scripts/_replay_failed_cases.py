#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "pyyaml"]
# ///
"""Surgical replay: for cells with transient exception rows, re-run ONLY
the failed case_names (not the whole cell), then merge the new rows into
the original CSV/JSONL. Output is a new timestamped result dir per cell
that show_results.py will pick up automatically (since it picks the
lexicographically latest dir).

This is a wrapper that for each cell, spawns a subprocess in the
benchmark dir that:
  1. Loads the same config as the original run
  2. Loads the dataset via the bench's expt module
  3. Filters dataset.cases to just the failed case_names
  4. Runs the bench's evaluator on the filtered dataset (writes a small
     "patch" CSV/JSONL under a temp result_dir)
After all per-cell subprocesses finish, this script merges each patch
CSV/JSONL into the corresponding original (exception rows replaced by
fresh ones) and saves to a new timestamped dir under the original
parent.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]  # orchestrator-results/

# Per-cell metadata (mirrors run_test_eval.sh's tables for the cells we
# care about — only musr cells have transients).
CELLS = [
    ("existing_workflow", "musr_murder",
     "musr/results/orchestration_learner/20260426.080629.orch_learner",
     "musr", "conf/murder_orchestrated.yaml",
     "dataset.split=murder_mysteries_test"),
    ("existing_workflow", "musr_object",
     "musr/results/orchestration_learner/20260426.093453.orch_learner",
     "musr", "conf/object_orchestrated.yaml",
     "dataset.split=object_placements_test"),
    ("existing_workflow", "musr_team",
     "musr/results/orchestration_learner/20260426.101513.orch_learner",
     "musr", "conf/team_orchestrated.yaml",
     "dataset.split=team_allocation_test"),
    ("seed_from_ptools", "musr_object",
     "musr/results/orchestration_learner/20260427.020456.orch_learner",
     "musr", "conf/object_orchestrated.yaml",
     "dataset.split=object_placements_test"),
    ("seed_from_ptools", "musr_team",
     "musr/results/orchestration_learner/20260427.024705.orch_learner",
     "musr", "conf/team_orchestrated.yaml",
     "dataset.split=team_allocation_test"),
    # Patched NBA seed: 2 transient 429s (nba_0_67, nba_2_31).
    # The "src" here points at the PATCHED artifact, not the original.
    ("seed_from_ptools_nba_fix", "rulearena_nba",
     "COMMON/orchestrator-results/_patched_artifacts/seed_from_ptools_nba_fix/20260504.085000.orch_learner",
     "rulearena", "conf/conf.yaml",
     "dataset.split=test dataset.domain=nba dataset.complexity=all"),
]


def find_failed_case_names(cls: str, bench: str) -> tuple[Path, list[str]]:
    cdir = ROOT / cls / bench
    runs = sorted([p for p in cdir.iterdir() if p.is_dir() and (p / "results.csv").exists()])
    latest = runs[-1]
    df = pd.read_csv(latest / "results.csv")
    mask = df["predicted_output"].astype(str).str.contains("exception raised", regex=False)
    return latest, df.loc[mask, "case_name"].tolist()


def auto_extra_bindings(conf_path: Path, evolved_path: Path, entry: str) -> list[str]:
    """Same logic as run_test_eval.sh's extra_bindings helper."""
    import re
    cfg = yaml.safe_load(conf_path.read_text()) or {}
    bound = set((cfg.get("ptools") or {}).keys())
    src = evolved_path.read_text()
    pat = re.compile(r"^@interface\b[^\n]*\n(?:^@\w[\w.]*[^\n]*\n)*^def\s+(\w+)\s*\(",
                     re.MULTILINE)
    out = []
    for m in pat.finditer(src):
        name = m.group(1)
        if name == entry or name in bound:
            continue
        out.append(f"ptools.{name}.method=simulate")
    return out


def _impl_yaml(src_dir: Path) -> tuple[str, str]:
    impl = yaml.safe_load((src_dir / "implementation.yaml").read_text())
    entry = list(impl)[0]
    fn = impl[entry]["fn"]
    return entry, fn


def replay_cell(cls: str, bench: str, src_rel: str, bench_dir: str,
                conf_rel: str, split_dotlist: str) -> Path | None:
    """Run a subprocess that filters to failed cases and writes a patch CSV.
    Returns the patch CSV path, or None if no failures.
    """
    src_dir = REPO / "benchmarks" / src_rel
    conf_path = REPO / "benchmarks" / bench_dir / conf_rel
    train_dir = ROOT / "_train_dirs" / cls / bench
    entry, fn = _impl_yaml(src_dir)
    extra = auto_extra_bindings(conf_path, src_dir / "ptools_evolved.py", entry)

    latest_run, failed_names = find_failed_case_names(cls, bench)
    if not failed_names:
        print(f"[{cls}/{bench}] no failed cases — skip")
        return latest_run, []

    print(f"[{cls}/{bench}] {len(failed_names)} failed cases: {failed_names}")
    print(f"  src={src_dir}  conf={conf_path}  fn={fn}  extra={extra}")

    # Use a temp dir for the patch run's output
    patch_root = ROOT / "_replay_patches" / cls / bench
    patch_root.mkdir(parents=True, exist_ok=True)

    # Build the inline script that runs in the bench dir
    failed_json = json.dumps(failed_names)
    extra_args_repr = repr(extra + [
        f"llm.model=together_ai/deepseek-ai/DeepSeek-V3.1",
        f"cachier.enable_caching=true",
        f"learn.train_dir={train_dir}",
        f"ptools.{entry}.method=direct",
        f"ptools.{entry}.fn={fn}",
        f"ptools.{entry}.learner=orch_learner",
        f"evaluate.entry_point={entry}",
        f"evaluate.result_dir={patch_root}",
        f"evaluate.expt_name=replay_failed",
        f"evaluate.record_details=true",
        f"evaluate.max_workers=4",
        f"dataset.n=null",
    ] + split_dotlist.split())

    code = f'''
import importlib, sys, json
from pathlib import Path

bench_dir = Path({str(REPO / "benchmarks" / bench_dir)!r})
sys.path.insert(0, str(bench_dir))
sys.path.insert(0, str({str(REPO / "src")!r}))

from secretagent import config
from secretagent.core import implement_via_config

dotlist = {extra_args_repr}
config.configure(yaml_file=str(bench_dir / {conf_rel!r}), dotlist=dotlist)
config.set_root(bench_dir)

import expt as bench_expt
split = config.require("dataset.split")

# Resolve ptools module the way each bench does
if hasattr(bench_expt, "_resolve_module"):
    ptools_module_name = bench_expt._resolve_module(split)
else:
    ptools_module_name = "ptools"
ptools = importlib.import_module(ptools_module_name)
implement_via_config(ptools, config.require("ptools"))

# Load and FILTER dataset to just the failed cases. Each bench's
# load_dataset has a different signature — inspect and call accordingly.
import inspect as _insp
sig = _insp.signature(bench_expt.load_dataset)
ld_kwargs = {{}}
for pname in sig.parameters:
    val = config.get(f"dataset.{{pname}}")
    if val is not None:
        ld_kwargs[pname] = val
dataset = bench_expt.load_dataset(**ld_kwargs).configure(
    shuffle_seed=config.get("dataset.shuffle_seed"),
    n=config.get("dataset.n"),
)
failed = set({failed_json})
all_n = len(dataset.cases)
dataset.cases = [c for c in dataset.cases if c.name in failed]
print(f"filtered: {{len(dataset.cases)}}/{{all_n}} cases")
assert len(dataset.cases) == len(failed), \\
    f"missing cases in dataset: wanted {{failed}}, got {{[c.name for c in dataset.cases]}}"

entry_iface = getattr(ptools, config.require("evaluate.entry_point"))

# Pick the right evaluator class for this bench
EvalCls = None
for name in ("MUSREvaluator","RuleArenaEvaluator","MedCalcEvaluator","NaturalPlanEvaluator"):
    if hasattr(bench_expt, name):
        EvalCls = getattr(bench_expt, name)
        break
assert EvalCls is not None, "couldnt find evaluator class on bench expt module"
# NaturalPlanEvaluator needs task arg; others are no-arg
import inspect
sig = inspect.signature(EvalCls)
if "task" in sig.parameters:
    evaluator = EvalCls(task=split)
else:
    evaluator = EvalCls()

csv_path = evaluator.evaluate(dataset, entry_iface)
print(f"PATCH_CSV={{csv_path}}")
'''
    proc = subprocess.run(
        ["uv", "run", "python", "-c", code],
        cwd=REPO / "benchmarks" / bench_dir,
        capture_output=True, text=True,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        raise RuntimeError(f"replay subprocess failed for {cls}/{bench}: rc={proc.returncode}")

    # Find patch CSV path from stdout
    patch_csv = None
    for line in proc.stdout.splitlines():
        if line.startswith("PATCH_CSV="):
            patch_csv = Path(line.split("=", 1)[1].strip())
            break
    assert patch_csv and patch_csv.exists(), f"patch CSV not found in stdout"
    return latest_run, [patch_csv]


def merge_patch_into_original(orig_run: Path, patch_csv: Path) -> Path:
    """Replace exception rows in original by case_name with new patch rows.
    Write merged CSV+JSONL to a new timestamped dir under the original parent.
    """
    parent = orig_run.parent
    orig_csv = orig_run / "results.csv"
    orig_jl = orig_run / "results.jsonl"
    patch_jl = patch_csv.parent / "results.jsonl"
    orig_cfg = orig_run / "config.yaml"

    df_orig = pd.read_csv(orig_csv)
    df_patch = pd.read_csv(patch_csv)

    # Replace by case_name
    keep_orig = df_orig[~df_orig["case_name"].isin(set(df_patch["case_name"]))]
    merged = pd.concat([keep_orig, df_patch], ignore_index=True)
    # Preserve original case order
    order = {n: i for i, n in enumerate(df_orig["case_name"])}
    merged = merged.sort_values(by="case_name", key=lambda s: s.map(order)).reset_index(drop=True)

    # New timestamped dir
    ts = datetime.now().strftime("%Y%m%d.%H%M%S")
    new_dir = parent / f"{ts}.test_deepseek_v3_1"
    new_dir.mkdir(parents=True, exist_ok=False)
    merged.to_csv(new_dir / "results.csv", index=False)

    # Merge JSONL too if both present
    if orig_jl.exists() and patch_jl.exists():
        patched_names = set(df_patch["case_name"])
        with (new_dir / "results.jsonl").open("w") as out:
            with orig_jl.open() as f:
                for line in f:
                    rec = json.loads(line)
                    if rec.get("case_name") in patched_names:
                        continue
                    out.write(line)
            with patch_jl.open() as f:
                for line in f:
                    out.write(line)

    if orig_cfg.exists():
        (new_dir / "config.yaml").write_text(orig_cfg.read_text())

    return new_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="comma-separated cls:bench filter")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None

    summary = []
    for cls, bench, src_rel, bench_dir, conf_rel, split_dotlist in CELLS:
        key = f"{cls}:{bench}"
        if only and key not in only:
            continue
        try:
            latest_run, patch_csvs = replay_cell(cls, bench, src_rel, bench_dir, conf_rel, split_dotlist)
        except Exception as e:
            print(f"[{key}] ERROR: {e}", file=sys.stderr)
            summary.append((key, "ERROR", str(e)))
            continue
        if not patch_csvs:
            summary.append((key, "NO-FAILURES", str(latest_run)))
            continue
        new_dir = merge_patch_into_original(latest_run, patch_csvs[0])
        # Re-summarize
        df = pd.read_csv(new_dir / "results.csv")
        n = len(df)
        exc = int(df['predicted_output'].astype(str).str.contains('exception raised', regex=False).sum())
        acc = df['correct'].mean() * 100
        summary.append((key, f"acc={acc:.1f}% exc={exc}/{n}", str(new_dir)))

    print("\n=== Replay summary ===")
    for k, status, where in summary:
        print(f"  {k:<35}  {status:<25}  {where}")


if __name__ == "__main__":
    main()
