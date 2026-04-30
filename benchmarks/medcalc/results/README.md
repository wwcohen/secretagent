# MedCalc Result Artifact Index

This file maps the timestamped result directories to the experiment names used in the report. Use `docs/medcalc_induction_report.md` for the full discussion and metrics.

## Workflow-Mode OrchestrationLearner Runs

These runs answer whether the learner has evolved ptools for the two workflow modes.

| Human label | Result directory | Final evolved ptools | Tracked scratch copy |
|---|---|---|---|
| Workflow provided / existing workflow | `benchmarks/medcalc/results/orchestration_learner/20260426.040958.orch_learner/` | `benchmarks/medcalc/results/orchestration_learner/20260426.040958.orch_learner/ptools_evolved.py` | `benchmarks/medcalc/.orchestration_learner/ptools_20260426.040958_scratch.py` |
| Workflow composed by orchestrator | `benchmarks/medcalc/results/orchestration_learner/20260426.182640.orch_learner/` | `benchmarks/medcalc/results/orchestration_learner/20260426.182640.orch_learner/ptools_evolved.py` | `benchmarks/medcalc/.orchestration_learner/ptools_20260426.182640_scratch.py` |

The run directories are the best place to inspect these experiments because each contains `report.json`, `report.html`, `implementation.yaml`, `run_metadata.json`, `ptools_evolved.py`, plots, final eval files, and per-iteration before/after files.

## Equation-Only / Rule-Only Induced Ptool Runs

These are the completed equation-only and rule-only split experiments.

| Human label | Source traces / induction output | Learner result directory | Final ptools |
|---|---|---|---|
| Equation-only induced ptools | `benchmarks/medcalc/learned/equation-4pc-pro-mp3/20260430.020302.calculate_medical_value__ptool_inducer/` | `benchmarks/medcalc/results/orchestration_learner/20260430.021235.orch_learner/` | `benchmarks/medcalc/ptools_induced_equation_evolved.py` |
| Rule-only induced ptools | `benchmarks/medcalc/learned/rule-4pc-pro-mp3/20260430.020806.calculate_medical_value__ptool_inducer/` | `benchmarks/medcalc/results/orchestration_learner/20260430.035155.orch_learner/` | `benchmarks/medcalc/ptools_induced_rule_evolved.py` |

Existing-benchmark evaluations for these final ptools are here:

- Equation-only: `benchmarks/medcalc/results/benchmark_eval/20260430.051051.equation_orch_on_existing_benchmark/`
- Rule-only: `benchmarks/medcalc/results/benchmark_eval/20260430.061531.rule_orch_on_existing_benchmark/`

## Trace Generation Runs

| Human label | Result directory | Summary |
|---|---|---|
| Equation trace generation, 4/calc train sample | `benchmarks/medcalc/results/20260430.004024.react_train_equation_4pc/` | 132 cases, 95/132 correct |
| Rule trace generation, 4/calc train sample | `benchmarks/medcalc/results/20260430.013446.react_train_rule_4pc/` | 76 cases, 39/76 correct |

## Not Used For Current Reported Metrics

Later equation-only/rule-only orchestrator runs may still be running from a separate terminal. Do not use partial directories from those runs as reported metrics until they are summarized in the report.
