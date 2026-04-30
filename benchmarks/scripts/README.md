# benchmarks/scripts/ — auxiliary canonical helpers

Companion scripts to the top-level `benchmarks/run_*.sh` v4 pipeline. Started
as `/tmp/*` one-shots; promoted here when they earned their keep.

| File | Purpose |
|---|---|
| `musr_obj_team_full.sh` | Full pipeline (Phase A→E) for `musr_object` + `musr_team` (the two musr tasks not covered by the original master_chain). Each task does workflow_train + react_train + val_baseline → class 1/2/3 v4 distill → vals. |
| `tabmwp_full.sh` | Full pipeline (Phase A→E) for tabmwp. Uses `conf/workflow_incontext.yaml` as the decomposable baseline (4-ptool: identify_operation / extract_relevant_values / compute_answer / format_answer). |
| `fill_missing_vals_v2.sh` | Fill missing v4 vals where the learned dir exists but val never ran: c1_v4 (musr_murder, medcalc, geometric, date, rulearena), c2_v4 (finqa, rulearena_nba/tax), c3_v4 (finqa, calendar). Excludes `c1_v1` (intentionally not run). |
| `fix_c2c3_failed.sh` | Recovers from the silent failure of Class 2 distill on musr (object/team) and tabmwp — root cause: raw HuggingFace-format JSON didn't satisfy `Dataset.model_validate_json`. This script (1) converts data to Dataset format via the benchmark's own `expt.load_dataset()` (2) re-runs Class 2 sequentially per task (3) re-runs Class 3 vals with induced ptools as `simulate` (not `learned_code`). |
| `fix_meeting_v3.sh` | Re-distill `meeting_planning` Class 2 with `golden_plan` list→str conversion. Without this, the LLM learns to return `list` (matches holdout 90%) but val evaluator expects `str` → 0%. Conversion lifts it to ~98%. |
| `scan_all_vals.py` | Walks every `val_results_full/`, `val_results/`, and archived `results/` dir under `benchmarks/`, extracts (n, acc, cost, model, split, expt_name) per run, applies BBH paren-strip post-hoc. Output: `/tmp/all_vals_scan.csv`. |
| `build_master_table.py` | Reads `/tmp/all_vals_scan.csv` and emits the master comparison table (acc / cost / n) at the bottom of `docs/code_distillation_results_v2.md`. Drops empty columns, marks running cells with 🏃, includes `v1_*` columns from the v1 doc text. |

## Convention

These all assume `cwd = secretagent/`. They use `$ROOT="/Users/.../secretagent"` and
read `$ROOT/.env` for API keys via `set -a; source ...; set +a`.

When kicked off in the background they write progress to
`benchmarks/codedistill_logs_v2/` and master logs to `/tmp/`.
