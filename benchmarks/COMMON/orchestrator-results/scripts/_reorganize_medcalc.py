#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "pyyaml"]
# ///
"""Restructure medcalc results to make 'which traces was the workflow
learned from' explicit at the directory level.

Before:
  <cls>/medcalc/final/{combined,formulas,rules}/<TS>/

After:
  <cls>/medcalc/final/learned_from_all_traces/{overall,formulas,rules}/<TS>/

Plus, under seed_from_ptools/medcalc/final/, add the user's two
per-category-trained variants (sourced from
benchmarks/medcalc/results/full_test_eval/):
  learned_from_formula_traces/overall/<TS>/   (660 cases, formula test set)
  learned_from_rules_traces/overall/<TS>/     (380 cases, rules test set)

Each new variant gets a results.csv that's the user's "retried" canonical
CSV (the un-retried first-attempt CSV is preserved alongside as
results_attempt1.csv for traceability).
"""

import shutil
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]  # orchestrator-results/
USER_FULL_TEST = ROOT.parents[1] / "medcalc" / "results" / "full_test_eval"


def stats(csv: Path) -> str:
    if not csv.exists():
        return "(no csv)"
    df = pd.read_csv(csv)
    n = len(df)
    acc = df["correct"].mean() * 100 if "correct" in df else float("nan")
    return f"n={n}, acc={acc:.2f}%"


def wrap_existing_partitions(cls: str) -> None:
    """Move final/{combined,formulas,rules} → final/learned_from_all_traces/{overall,formulas,rules}."""
    final = ROOT / cls / "medcalc" / "final"
    if not final.is_dir():
        print(f"  {cls}/medcalc/final missing")
        return
    new_parent = final / "learned_from_all_traces"
    new_parent.mkdir(exist_ok=True)
    rename_map = [("combined", "overall"), ("formulas", "formulas"), ("rules", "rules")]
    for old_name, new_name in rename_map:
        src = final / old_name
        dst = new_parent / new_name
        if not src.is_dir():
            continue
        if src.parent == new_parent and old_name == new_name:
            continue
        if dst.exists():
            continue
        shutil.move(str(src), str(dst))
        print(f"  {cls}/medcalc/final/{old_name} → final/learned_from_all_traces/{new_name}")


def import_user_run(src_dir: Path, dst_dir: Path, canonical_csv_name: str) -> None:
    """Copy the user's full_test_eval run dir into our layout. Rename the
    canonical CSV to results.csv; preserve other CSVs alongside."""
    if not src_dir.is_dir():
        print(f"  source missing: {src_dir}")
        return
    if dst_dir.exists():
        print(f"  destination exists, skipping: {dst_dir}")
        return
    dst_dir.mkdir(parents=True)

    # Copy each file; rename canonical to results.csv
    for src_file in src_dir.iterdir():
        if not src_file.is_file():
            continue
        if src_file.name == canonical_csv_name:
            target = dst_dir / "results.csv"
        elif src_file.name == "results.csv":
            target = dst_dir / "results_attempt1.csv"
        else:
            target = dst_dir / src_file.name
        shutil.copy2(str(src_file), str(target))
    print(f"  imported {src_dir} → {dst_dir} (canonical = {canonical_csv_name})")


def update_provenance(cls: str) -> None:
    cell = ROOT / cls / "medcalc"
    final = cell / "final"
    text = f"# {cls}/medcalc\n\n## final/\n\n"
    for variant_dir in sorted([p for p in final.iterdir() if p.is_dir() and p.name.startswith("learned_from_")]):
        text += f"### {variant_dir.name}/\n"
        for sub in sorted([p for p in variant_dir.iterdir() if p.is_dir()]):
            for run in sorted([p for p in sub.iterdir() if p.is_dir()]):
                text += f"- `{variant_dir.name}/{sub.name}/{run.name}/` — {stats(run/'results.csv')}\n"
        text += "\n"
    text += """## What 'learned from X traces' means

- **all_traces**: orch_learner trained on the full medcalc training set (mixed
  formula + rule categories). One workflow handles every case.
- **formula_traces** *(seed_from_ptools only)*: orch_learner trained on only
  the formula categories (dosage, lab test, physical). The `overall/` test
  set is the 660-case formula partition of medcalc test.
- **rules_traces** *(seed_from_ptools only)*: orch_learner trained on only
  the rules categories (diagnosis, risk, severity). The `overall/` test
  set is the 380-case rules partition of medcalc test.

The `formulas/` and `rules/` subdirs under `learned_from_all_traces/` are
post-hoc category filters of the 1100-case `overall/` run, so they're
directly comparable to the `learned_from_formula_traces/overall/` and
`learned_from_rules_traces/overall/` runs above (same case counts).
"""
    (cell / "PROVENANCE.md").write_text(text)
    print(f"  wrote {cell/'PROVENANCE.md'}")


def main() -> None:
    print("=== wrap existing medcalc partitions under learned_from_all_traces/ ===")
    for cls in ("existing_workflow", "seed_from_ptools"):
        wrap_existing_partitions(cls)

    print("\n=== import user's per-category runs into seed_from_ptools/medcalc/final/ ===")
    seed_final = ROOT / "seed_from_ptools" / "medcalc" / "final"
    import_user_run(
        USER_FULL_TEST / "20260503.223737.formula_evolved_deepseek_v31_full_test",
        seed_final / "learned_from_formula_traces" / "overall" / "20260503.223737.formula_evolved_deepseek_v31_full_test",
        "results_retried2.csv",
    )
    import_user_run(
        USER_FULL_TEST / "20260504.014529.rule_evolved_deepseek_v31_full_test",
        seed_final / "learned_from_rules_traces" / "overall" / "20260504.014529.rule_evolved_deepseek_v31_full_test",
        "results_retried.csv",
    )

    print("\n=== update PROVENANCE.md for each medcalc cell ===")
    for cls in ("existing_workflow", "seed_from_ptools"):
        update_provenance(cls)


if __name__ == "__main__":
    main()
