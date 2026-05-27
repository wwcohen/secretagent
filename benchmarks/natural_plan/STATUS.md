# natural_plan — migration status

_Last updated: 2026-05-27_

The `natural_plan` benchmark (sub-tasks: `meeting`, `calendar`, `trip`) was migrated
to the repo-standard conventions: each sub-task is a self-contained benchmark using the
generic `secretagent.cli.expt` runner, anchored output paths, and `data/{train,valid,test}.json`
splits.

## Done

### 1. Output-path scheme (`${pathto.task}`)
All sub-task conf files now anchor outputs to the benchmark dir, matching
`benchmarks/bbh/sports_understanding`:

```yaml
pathto:
  task: ${pathto.repo}/benchmarks/natural_plan/<subtask>
  logs: ${pathto.task}
cachier:
  cache_dir: ${pathto.task}/llm_cache
evaluate:
  result_dir: ${pathto.logs}/results
```

Outputs land in `<subtask>/llm_cache` and `<subtask>/results` regardless of launch dir
(replaces the deprecated bare-relative + `config.set_root(cwd)` scheme).

### 2. Data → `data/{train,valid,test}.json`
- Renamed the stratified splits to `<subtask>/data/{train,valid,test}.json` (repo standard);
  removed legacy `_50` and `_train_paper` files; kept the raw pools
  (`*_planning.json` / `*_scheduling.json`).
- `data/partition.py` rewritten for the per-subtask layout. Splits are 100 each, stratified,
  disjoint (train=seed 42, valid=43, test=44), prompt_0shot baked in. **Regeneration
  reproduces the existing 9 splits exactly** (same cases, same order).
- Runtime sampling knobs are gone (`prompt_mode`, `stratified`, `sample_n`, `sample_seed`,
  `partition`): stratified + prompt_0shot are now fixed in the split files. New variants
  come from `partition.py`.

### 3. Per-subtask no-arg evaluators
`<subtask>/evaluator.py` defines a no-arg `Evaluator` subclass
(`MeetingEvaluator` / `CalendarEvaluator` / `TripEvaluator`) that supplies
`compare_predictions` using the scoring fns in the shared `eval_utils.py`. Invoked via
`--evaluator evaluator.<Class>`.

### 4. Conf files (11 total)
- `evaluate.entry_point: X` → `evaluate.root_interface: ptools.X`
- `evaluate.prompt_trace: true` → `evaluate.record_details: true` (full rollouts captured
  into `results.jsonl`; the base `Evaluator` handles it — no custom `evaluate()` / no
  `prompt_trace.jsonl` / no `run_summary.json`)
- `dataset.split` defaults: main configs (`<task>.yaml`) → `valid`; trace/learning configs
  (`*_zs_cot`, `*_self_improve`, `*_induced_seed_from_ptools`) → `train`

### 5. Makefiles → `cli.expt`
Targets now call `uv run python -m secretagent.cli.expt run --config conf/X.yaml
--evaluator evaluator.<Class> …`. The `DATASET_PARTITION` override (meeting/calendar) now
sets `dataset.split`; stale `--check dataset.split=<task>` removed from `export`.

### 6. Removed
- Bespoke `natural_plan/expt.py` (deleted).
- Orphaned top-level `natural_plan/{llm_cache,results}` from old task-set-level runs.

### How to run now (per sub-task)
```
cd benchmarks/natural_plan/<subtask>
make structured_baseline          # or workflow / pot / react / unstructured_baseline
make DATASET_PARTITION=test structured_baseline   # run on the test split (meeting/calendar)
```

## To do

- [ ] **Deferred search/pareto + batch tooling still references the deleted `expt.py`**
  (left for the other branch): `run_pareto.py`, `meeting/nsga2.yaml`, `trip/nsga2.yaml`,
  `scripts/run_all_15.py`, `scripts/report.py`. Update to `-m secretagent.cli.expt … --evaluator …`
  or remove.
- [ ] **Align `meeting/` and `calendar/` Makefiles** to the cleaner `trip/` pattern
  (`EXPT = …` + `basics:` aggregate target) instead of `MEET_BASE`/`CAL_BASE` +
  `PARTITION_OVERRIDE`.
- [ ] **Reconsider `record_details: true` on the main eval configs** (`<task>.yaml`): it
  embeds full rollouts in every `results.jsonl`, which is heavy for plain accuracy/cost runs.
  Option: move it to recording/learning targets only (cf. `bbh/sports_understanding/Makefile.learning-demo`).
- [ ] **Run a live smoke test** to confirm the full LLM path end-to-end (migration was
  verified zero-cost only). `calendar/` has a `smoke` target (CAL_N=5).
- [ ] **Confirm split defaults** (main→`valid`, trace/learning→`train`) are what you want.
