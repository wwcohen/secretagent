#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas"]
# ///
"""Reorganize each cell into final/ + archive/ for clarity.

Before:
    <cls>/<bench>/<TS1>.test_deepseek_v3_1/  (older, e.g. pre-replay)
    <cls>/<bench>/<TS2>.test_deepseek_v3_1/  (current, e.g. post-replay)

After:
    <cls>/<bench>/final/<TS2>.test_deepseek_v3_1/   (canonical)
    <cls>/<bench>/archive/<TS1>.test_deepseek_v3_1/ (older)
    <cls>/<bench>/PROVENANCE.md

medcalc has partition subdirs (combined/formulas/rules), each with one
run; we just move them under final/.
"""

import shutil
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]  # orchestrator-results/

# (cls, bench, final_run_basename, why_this_one)
PLAN = [
    ("existing_workflow", "musr_murder",      "20260504.115248.test_deepseek_v3_1", "post-replay; 14 transients reduced to 3, acc 59→68"),
    ("existing_workflow", "musr_object",      "20260504.115652.test_deepseek_v3_1", "post-replay; 1 transient cleared, acc 63.21→64.15"),
    ("existing_workflow", "musr_team",        "20260504.120019.test_deepseek_v3_1", "post-replay; 8 'cannot find final answer' are persistent (not transient)"),
    ("existing_workflow", "natplan_calendar", "20260504.003526.test_deepseek_v3_1", "single run, 7.0%"),
    ("existing_workflow", "natplan_meeting",  "20260504.043842.test_deepseek_v3_1", "single run, 100% (algorithmic Python solver)"),
    ("existing_workflow", "natplan_trip",     "20260504.071806.test_deepseek_v3_1", "single run, 11.0%"),
    ("existing_workflow", "rulearena_nba",    "20260504.002114.test_deepseek_v3_1", "parallel-orchestrator run; smoke run (54.35%) archived"),
    ("seed_from_ptools",  "musr_murder",      "20260504.031321.test_deepseek_v3_1", "single run, 76.0%, no transients"),
    ("seed_from_ptools",  "musr_object",      "20260504.120348.test_deepseek_v3_1", "post-replay; 6 'cannot find final answer' are persistent"),
    ("seed_from_ptools",  "musr_team",        "20260504.120734.test_deepseek_v3_1", "post-replay; 4 'cannot find final answer' are persistent"),
    ("seed_from_ptools",  "natplan_calendar", "20260504.024653.test_deepseek_v3_1", "single run, 28.0%"),
    ("seed_from_ptools",  "natplan_meeting",  "20260504.044021.test_deepseek_v3_1", "single run, 75.0%"),
    ("seed_from_ptools",  "natplan_trip",     "20260504.082218.test_deepseek_v3_1", "single run, 100% (algorithmic Python solver)"),
    ("seed_from_ptools",  "rulearena_nba",    "20260504.005211.test_deepseek_v3_1", "single run, 26.1% (uses raw problem text only — see seed_from_ptools_nba_fix for patched version)"),
    ("seed_from_ptools_nba_fix", "rulearena_nba", "20260504.121504.test_deepseek_v3_1",
     "post-replay; 1 persistent pydantic schema-validation failure (nba_2_31). Patched workflow: includes CBA rules + structured metadata in extract_nba_params query (lifted seed from 26.1% to 65.2%, beating existing's 52.2%)"),
]


def cell_stats(csv_path: Path) -> str:
    if not csv_path.exists():
        return "(no results.csv)"
    df = pd.read_csv(csv_path)
    n = len(df)
    acc = df["correct"].mean() * 100 if "correct" in df else float("nan")
    exc = (df["predicted_output"].astype(str).str.contains("exception raised", regex=False).sum()
           if "predicted_output" in df else 0)
    cost = df["cost"].sum() if "cost" in df else 0.0
    return f"n={n}, acc={acc:.2f}%, exc={int(exc)}, cost=${cost:.3f}"


def reorg_cell(cls: str, bench: str, final_basename: str, why: str) -> None:
    cell = ROOT / cls / bench
    if not cell.is_dir():
        print(f"  SKIP {cls}/{bench} (no dir)")
        return

    runs = [p for p in cell.iterdir()
            if p.is_dir() and p.name.endswith(".test_deepseek_v3_1")
            and (p / "results.csv").exists()]
    if not runs:
        print(f"  SKIP {cls}/{bench} (no runs)")
        return

    final_dir = cell / "final"
    archive_dir = cell / "archive"
    final_dir.mkdir(exist_ok=True)
    archive_dir.mkdir(exist_ok=True)

    final_path = cell / final_basename
    if not final_path.exists():
        print(f"  ERROR {cls}/{bench}: chosen final {final_basename} not found")
        return

    # Move final
    new_final = final_dir / final_basename
    if not new_final.exists():
        shutil.move(str(final_path), str(new_final))
        print(f"  {cls}/{bench}/final/{final_basename}  ({cell_stats(new_final/'results.csv')})")

    # Move others to archive
    for run in runs:
        if run.name == final_basename:
            continue
        if not run.exists():
            continue  # already moved
        target = archive_dir / run.name
        if target.exists():
            continue
        shutil.move(str(run), str(target))
        print(f"  {cls}/{bench}/archive/{run.name}  ({cell_stats(target/'results.csv')})")

    # Write PROVENANCE.md
    prov = cell / "PROVENANCE.md"
    final_csv = new_final / "results.csv"
    archived = sorted([p.name for p in archive_dir.iterdir() if p.is_dir()])
    text = f"""# {cls}/{bench}

## final/
- `{final_basename}/` — {cell_stats(final_csv)}
- chosen because: {why}

## archive/
"""
    if archived:
        for a in archived:
            text += f"- `{a}/` — {cell_stats(archive_dir/a/'results.csv')}\n"
    else:
        text += "(empty — only one run)\n"
    prov.write_text(text)


def reorg_medcalc(cls: str) -> None:
    """medcalc has combined/formulas/rules subdirs; nest them under final/."""
    cell = ROOT / cls / "medcalc"
    if not cell.is_dir():
        return
    final_dir = cell / "final"
    final_dir.mkdir(exist_ok=True)
    moved = []
    for subdir in ("combined", "formulas", "rules"):
        src = cell / subdir
        if not src.is_dir() or not src.exists():
            continue
        # Skip if already under final
        if src.parent.name == "final":
            continue
        dst = final_dir / subdir
        if dst.exists():
            continue
        shutil.move(str(src), str(dst))
        moved.append(subdir)
    # PROVENANCE
    prov = cell / "PROVENANCE.md"
    text = f"# {cls}/medcalc\n\n## final/\n"
    for sub in ("combined", "formulas", "rules"):
        sub_dir = final_dir / sub
        if sub_dir.is_dir():
            for run in sub_dir.iterdir():
                if run.is_dir():
                    text += f"- `{sub}/{run.name}/` — {cell_stats(run/'results.csv')}\n"
    text += "\nmedcalc was run as one workflow over the full 1100-case test set; "
    text += "`combined/` is that full set, `formulas/` and `rules/` are post-hoc category filters.\n"
    prov.write_text(text)


def main() -> None:
    print("=== reorganizing cells ===")
    for cls, bench, final, why in PLAN:
        reorg_cell(cls, bench, final, why)
    print("\n=== reorganizing medcalc partition dirs ===")
    for cls in ("existing_workflow", "seed_from_ptools"):
        reorg_medcalc(cls)
    print("\n=== writing top-level README ===")
    readme = ROOT / "RESULTS_LAYOUT.md"
    readme.write_text("""# Results layout

Each cell sits at `<class>/<bench>/` and contains:

```
<cell>/
├── final/<TS>.test_deepseek_v3_1/   # the canonical result for this cell
│   ├── results.csv                  # one row per case
│   ├── results.jsonl                # full per-case rollouts
│   └── config.yaml                  # exact config used
├── archive/<TS>.test_deepseek_v3_1/ # older runs (pre-replay, smoke, etc.)
└── PROVENANCE.md                    # which run is final and why
```

medcalc has three partition views inside `final/`: `combined/` (all 1100
cases), `formulas/` (660 cases: dosage, lab test, physical), `rules/`
(380 cases: diagnosis, risk, severity).

## Classes

- **existing_workflow** — orch_learner started from the configured workflow
- **seed_from_ptools** — orch_learner started from a seeded ptools-based config
- **seed_from_ptools_nba_fix** — manual patch to seed/rulearena_nba's workflow
  to include CBA rules + structured metadata in the NBA query (lifts accuracy
  from 26.1% to 65.2%; see `_patched_artifacts/seed_from_ptools_nba_fix/.../PATCH_NOTES.md`)

## Helper scripts (infra, not results)

- `run_test_eval.sh` — single-cell driver
- `run_parallel.sh` — multi-lane orchestrator
- `show_results.py` — summary table over `final/` results
- `_replay_failed_cases.py` — surgical rerun of just the exception-row cases
- `_train_dirs/`, `_patched_artifacts/`, `_replay_patches/`, `_logs/` — infrastructure
""")
    print("done")


if __name__ == "__main__":
    main()
