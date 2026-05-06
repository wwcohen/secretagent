# Orchestrator Results

Test-set re-evaluation of the eight orchestration_learner workflows
documented in `docs/orchestration_learner_sweep_results.md`. Every cell
was run on the held-out test split with
`together_ai/deepseek-ai/DeepSeek-V3.1`.

The canonical layout now matches the COMMON codedistill result layout:

```
<bench>/
  test_results_full/
    <TS>.<subbench>_test_full_orch_existing_workflow/
    <TS>.<subbench>_test_full_orch_seed_from_ptools/
```

The preserved legacy layout is still present under `existing_workflow/` and
`seed_from_ptools/` for provenance and debugging. The canonical test table uses:

- `orch_existing_workflow`: hand workflow + orchestrator-improved ptools
- `orch_seed_from_ptools`: orchestrator-generated workflow + orchestrator-improved ptools

`medcalc` is always split into `medcalc_formulas` and `medcalc_rules`; the
overall mixed result is not used for headline tables. `rulearena_nba` uses the
default unpatched seed run (`without_rulebook`); manual rulebook-fix artifacts
remain in the legacy tree but are excluded by default.

```bash
# Print the two canonical test-set summary tables:
bash benchmarks/COMMON/orchestrator-results/show_summary.sh

# Machine-readable extraction:
uv run --script benchmarks/COMMON/orchestrator-results/scripts/show_results.py \
  --md /tmp/orchestrator_results.md \
  --csv /tmp/orchestrator_results.csv
```

See `RESULTS_LAYOUT.md` for the directory layout and the meaning of the
`with_rulebook` / `without_rulebook` and `learned_from_*_traces`
variants.

Helper scripts and infra dirs live under `scripts/`.
