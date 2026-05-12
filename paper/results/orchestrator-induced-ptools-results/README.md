# Orchestrator Induced Ptools Results

Held-out DeepSeek V3.1 test re-evaluations for orchestrator-generated workflows
that use induced seed ptools. The canonical layout matches the COMMON
codedistill result layout for non-MedCalc benchmarks:

```
<bench>/
  test_results_full/
    <TS>.<subbench>_test_full_orch_induced_seed_ptools/
```

MedCalc is stored as paper-facing split result files:

```
medcalc/formulas/results.csv
medcalc/rules/results.csv
```

Condition:

- `orch_induced_seed_ptools`: orchestrator-generated workflow + induced seed ptools

Canonical rows:

- `medcalc_formulas`
- `medcalc_rules`
- `musr_murder`
- `musr_object`
- `musr_team`
- `natplan_meeting`
- `natplan_trip`
- `rulearena_nba`

The mixed `medcalc/overall` result is preserved but intentionally excluded from
the headline summary table.

The source final eval runs remain in their benchmark-local
`test_results_full/` directories. Learner outputs remain under each
benchmark's `results/orchestration_learner/*.orch_learner/` directories.
The optional rerun index under `benchmarks/COMMON/orchestrator-results/_train_dirs/`
uses repo-relative pointer files rather than committed directory symlinks, so it
works on checkouts where Git cannot create symlinks.

```bash
# Print the canonical test-set summary table:
bash benchmarks/COMMON/orchestrator-induced-ptools-results/show_summary.sh

# Machine-readable extraction:
uv run --script benchmarks/COMMON/orchestrator-induced-ptools-results/scripts/show_results.py \
  --md /tmp/orchestrator_induced_ptools_results.md \
  --csv /tmp/orchestrator_induced_ptools_results.csv
```

Verification notes from the final run:

- Final eval used normal benchmark configs with learned direct entry bindings.
- NaturalPlan final eval was capped to the planned 100 rows via `dataset.n=100`.
- Cache was disabled in the final eval runner to avoid slow cache loading.
- Summary handling accepts boolean CSV `correct` values.
