# benchmarks/jerry/ — archived scripts

Scripts that are no longer canonical but worth keeping for traceability of how
the opus results were arrived at. **Do not run these — they may reference paths /
configs that have since changed.** For canonical pipeline see top-level
`benchmarks/run_*.sh` (Phase A/B/C/D/E opus) and `benchmarks/scripts/` (helpers).

## Subdirectories

| Dir | What | When superseded |
|---|---|---|
| `class1_iters/` | Earlier iterations of the Class 1 (ptool codedistill) sweep — v1 (loose `train_wrong_rate`, `only_correct=False`), v2 (first val gate, mini sizes), v3 (mid-iter snapshot), v5 (gate-metric ablation: `train` vs `val`) | by `run_class1_opus_full_codedistill.sh` (full-size, `val_wrong_rate ≤ 0.20`, `only_correct=True`) |
| `class2_iters/` | Earlier iterations of Class 2 (workflow distill on hand tools) — v1 mini, v2 mini, v3 partial. None used `backoff=simulate` | by `run_class2_opus_full_workflow.sh` (full-size, backoff=simulate) |
| `class3_iters/` | Earlier iterations of Class 3 (workflow distill on induced ptools) — v1 ptool inducer only, v2 mini | by `run_class3_opus_full.sh` (full pipeline incl. `_REACT_STATE` for musr) |
| `sweeps_pareto/` | Early grid sweeps and pareto-frontier analyses across many models / strategies. Predates the 3-class framework | by individual class scripts |
| `old_eval/` | Interim val-eval helpers used during the v2/v3 phase. `run_final.sh` and `run_remaining_evals.sh` were ad-hoc patches | by `run_full_size_val_eval.sh` |
| `tmp_relics/` | One-shot scripts that lived only in `/tmp/` during a run. Includes the original `master_chain.sh`, the killed `fill_missing_vals.sh` (had a c1_v1 step the user later vetoed), `fix_class1_opus_val.sh` (dotlist-bug fix), `fix_meeting_c2.sh` (the v2 prompt-only meeting fix that produced 0%), `wakeup_at.sh`, `inspect_all_benchmarks.py` | superseded by `benchmarks/scripts/` versions |

## How to map an archived run back to opus

If `benchmarks/<bench>/learned/`, `learned_v2/`, `learned_v3/` exists with a
non-empty `codedistill_config.yaml`, the corresponding sweep script lives in
`jerry/class1_iters/run_class1_v{1,2,3}_codedistill.sh`.

If `benchmarks/<bench>/learned_class2/`, `learned_class2_v2/`, `learned_class2_v3/`
exists, see `jerry/class2_iters/`. Same pattern for Class 3.

The opus output dirs (`learned_opus/`, `learned_class2_opus/`, `learned_class3_opus/`)
are produced by the canonical scripts under `benchmarks/run_*opus*.sh`.
