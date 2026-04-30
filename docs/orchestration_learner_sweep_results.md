# Orchestration Learner Sweep Results

Interactive curves: [orchestration_learner_sweep_curves.html](orchestration_learner_sweep_curves.html).
Research questions and findings: [orchestration_learner_research_findings.html](orchestration_learner_research_findings.html).

## Checked-In Artifact Locations

- Run scripts: `scripts/orchestrator_learner/`
- Sweep report: `docs/orchestration_learner_sweep_results.md`
- Interactive curves: `docs/orchestration_learner_sweep_curves.html`
- Research findings dashboard: `docs/orchestration_learner_research_findings.html`
- Checked-in result roots referenced by this report:
  - `benchmarks/finqa/results/orchestration_learner/`
  - `benchmarks/medcalc/results/orchestration_learner/`
  - `benchmarks/musr/results/orchestration_learner/`
  - `benchmarks/natural_plan/results/orchestration_learner/`
  - `benchmarks/rulearena/results/orchestration_learner/`
  - `benchmarks/tabmwp/results/orchestration_learner/`
  - `benchmarks/bbh/sports_understanding/results/orchestration_learner/`
  - `benchmarks/bbh/geometric_shapes/results/orchestration_learner/`
  - `benchmarks/bbh/penguins_in_a_table/results/orchestration_learner/`

Each timestamped `*.orch_learner/` directory listed in the table contains the checked-in learner artifacts for that run, including `run_metadata.json`, `report.json`, `implementation.yaml`, evolved ptools such as `ptools_evolved.py`, iteration snapshots, and `final_eval/*/results.csv`.

## Summary

- Runs: 30
- Benchmarks: 15
- Experiment classes: 2
- Runs with any evaluated best-eval improvement: 16
- Runs with retained final-eval improvement: 16
- No-op learner attempts: 33 across 9 runs

RuleArena airline, NBA, and tax each ran both experiment classes with baseline plus five learner attempts. Their post-baseline attempts made no code changes (`ptools_before.py` equals `ptools_after.py`), so those attempts have no new train/eval result directories. The HTML shows them as gray carried-forward markers, and best T/E is selected only from actually evaluated points.

TabMWP's final-eval `0.0%` entries should be treated as an instrumentation issue, not as evidence that the learned workflow lost all capability. The per-iteration evals were `50.0%`, but final eval reloads the evolved ptools after the one-time setup hook has already populated the benchmark table store; that reload clears the in-memory `_TABLE_STORE`, so later examples cannot recover their tables.

## Table

| Class | Benchmark | Initial T/E | Best T, T/E | Best E, T/E | Final T/E | Eval iters | No-op | Output |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `existing_workflow` | `finqa` | 66.2% / 58.9% | 0 / 66.2% / 58.9% | 0 / 66.2% / 58.9% | 66.2% / 58.9% | 6 / 6 | 0 | `20260426.033939.orch_learner` |
| `existing_workflow` | `medcalc` | 79.3% / 65.9% | 0 / 79.3% / 65.9% | 4 / 76.7% / 72.0% | 79.3% / 67.1% | 6 / 6 | 0 | `20260426.040958.orch_learner` |
| `existing_workflow` | `musr_murder` | 72.9% / 73.3% | 3 / 80.0% / 80.0% | 4 / 70.0% / 86.7% | 80.0% / 80.0% | 6 / 6 | 0 | `20260426.080629.orch_learner` |
| `existing_workflow` | `musr_object` | 55.4% / 46.9% | 5 / 77.0% / 78.1% | 5 / 77.0% / 78.1% | 77.0% / 78.1% | 6 / 6 | 0 | `20260426.093453.orch_learner` |
| `existing_workflow` | `musr_team` | 72.9% / 63.3% | 0 / 72.9% / 63.3% | 0 / 72.9% / 63.3% | 72.9% / 63.3% | 6 / 6 | 0 | `20260426.101513.orch_learner` |
| `existing_workflow` | `natural_plan_calendar` | 55.7% / 70.0% | 0 / 55.7% / 70.0% | 0 / 55.7% / 70.0% | 55.7% / 70.0% | 2 / 6 | 1 | `20260426.105044.orch_learner` |
| `existing_workflow` | `natural_plan_meeting` | 31.4% / 33.3% | 1 / 100.0% / 100.0% | 1 / 100.0% / 100.0% | 100.0% / 100.0% | 5 / 6 | 1 | `20260426.113321.orch_learner` |
| `existing_workflow` | `natural_plan_trip` | 47.1% / 50.0% | 0 / 47.1% / 50.0% | 0 / 47.1% / 50.0% | 47.1% / 50.0% | 6 / 6 | 0 | `20260426.115603.orch_learner` |
| `existing_workflow` | `rulearena_airline` | 28.6% / 16.7% | 0 / 28.6% / 16.7% | 0 / 28.6% / 16.7% | 28.6% / 16.7% | 1 / 6 | 5 | `20260426.132421.orch_learner` |
| `existing_workflow` | `rulearena_nba` | 89.7% / 61.5% | 0 / 89.7% / 61.5% | 0 / 89.7% / 61.5% | 89.7% / 61.5% | 1 / 6 | 5 | `20260426.133534.orch_learner` |
| `existing_workflow` | `rulearena_tax` | 0.0% / 0.0% | 0 / 0.0% / 0.0% | 0 / 0.0% / 0.0% | 0.0% / 0.0% | 1 / 6 | 5 | `20260426.134548.orch_learner` |
| `existing_workflow` | `tabmwp` | 54.3% / 50.0% | 0 / 54.3% / 50.0% | 0 / 54.3% / 50.0% | 54.3% / 0.0% | 6 / 6 | 0 | `20260426.135522.orch_learner` |
| `existing_workflow` | `sports_understanding` | 90.6% / 100.0% | 2 / 100.0% / 100.0% | 0 / 90.6% / 100.0% | 100.0% / 100.0% | 6 / 6 | 0 | `20260426.143640.orch_learner` |
| `existing_workflow` | `geometric_shapes` | 54.7% / 50.0% | 5 / 96.2% / 86.4% | 1 / 94.3% / 86.4% | 96.2% / 86.4% | 6 / 6 | 0 | `20260426.145831.orch_learner` |
| `existing_workflow` | `penguins_in_a_table` | 86.7% / 53.8% | 4 / 100.0% / 61.5% | 5 / 100.0% / 92.3% | 100.0% / 92.3% | 6 / 6 | 0 | `20260426.154538.orch_learner` |
| `seed_from_ptools` | `finqa` | 66.2% / 63.3% | 1 / 74.3% / 65.6% | 4 / 74.3% / 68.9% | 74.3% / 68.9% | 5 / 6 | 1 | `20260426.160710.orch_learner` |
| `seed_from_ptools` | `medcalc` | 56.0% / 48.8% | 5 / 82.9% / 72.0% | 4 / 81.9% / 74.4% | 82.9% / 72.0% | 6 / 6 | 0 | `20260426.182640.orch_learner` |
| `seed_from_ptools` | `musr_murder` | 72.9% / 73.3% | 5 / 77.1% / 90.0% | 5 / 77.1% / 90.0% | 77.1% / 90.0% | 6 / 6 | 0 | `20260427.012653.orch_learner` |
| `seed_from_ptools` | `musr_object` | 55.4% / 46.9% | 5 / 68.9% / 62.5% | 5 / 68.9% / 62.5% | 68.9% / 62.5% | 6 / 6 | 0 | `20260427.020456.orch_learner` |
| `seed_from_ptools` | `musr_team` | 72.9% / 63.3% | 3 / 85.7% / 86.7% | 3 / 85.7% / 86.7% | 85.7% / 86.7% | 6 / 6 | 0 | `20260427.024705.orch_learner` |
| `seed_from_ptools` | `natural_plan_calendar` | 55.7% / 66.7% | 5 / 88.6% / 93.3% | 4 / 85.7% / 100.0% | 88.6% / 93.3% | 5 / 6 | 0 | `20260427.033515.orch_learner` |
| `seed_from_ptools` | `natural_plan_meeting` | 31.4% / 33.3% | 3 / 82.9% / 70.0% | 4 / 82.9% / 83.3% | 82.9% / 83.3% | 6 / 6 | 0 | `20260427.050955.orch_learner` |
| `seed_from_ptools` | `natural_plan_trip` | 47.1% / 50.0% | 4 / 100.0% / 100.0% | 4 / 100.0% / 100.0% | 100.0% / 100.0% | 5 / 6 | 0 | `20260427.070108.orch_learner` |
| `seed_from_ptools` | `rulearena_airline` | 0.0% / 0.0% | 0 / 0.0% / 0.0% | 0 / 0.0% / 0.0% | 0.0% / 0.0% | 1 / 6 | 5 | `20260427.075326.orch_learner` |
| `seed_from_ptools` | `rulearena_nba` | 89.7% / 76.9% | 0 / 89.7% / 76.9% | 0 / 89.7% / 76.9% | 89.7% / 76.9% | 1 / 6 | 5 | `20260427.080244.orch_learner` |
| `seed_from_ptools` | `rulearena_tax` | 0.0% / 0.0% | 0 / 0.0% / 0.0% | 0 / 0.0% / 0.0% | 0.0% / 0.0% | 1 / 6 | 5 | `20260427.081032.orch_learner` |
| `seed_from_ptools` | `tabmwp` | 55.7% / 50.0% | 0 / 55.7% / 50.0% | 0 / 55.7% / 50.0% | 55.7% / 0.0% | 6 / 6 | 0 | `20260427.081905.orch_learner` |
| `seed_from_ptools` | `sports_understanding` | 90.6% / 100.0% | 1 / 100.0% / 100.0% | 0 / 90.6% / 100.0% | 100.0% / 100.0% | 6 / 6 | 0 | `20260427.083304.orch_learner` |
| `seed_from_ptools` | `geometric_shapes` | 52.8% / 54.5% | 2 / 100.0% / 95.5% | 5 / 100.0% / 100.0% | 100.0% / 100.0% | 6 / 6 | 0 | `20260427.085254.orch_learner` |
| `seed_from_ptools` | `penguins_in_a_table` | 86.7% / 53.8% | 5 / 100.0% / 76.9% | 3 / 83.3% / 92.3% | 100.0% / 76.9% | 6 / 6 | 0 | `20260427.094749.orch_learner` |

## Conclusions

The learner improved eval most clearly when it produced concrete, evaluated orchestration edits. Seeded workflows helped several compositional tasks, but also exposed brittle zero-accuracy cases. RuleArena is currently a failure-to-edit signal rather than a useful search curve, because supervisor attempts did not produce an applied code delta.
