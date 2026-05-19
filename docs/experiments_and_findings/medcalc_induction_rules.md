# MedCalc Formulas/Rules Orchestration Rerun

**Date:** 2026-05-01
**Purpose:** Rerun the formulas-only and rules-only OrchestrationLearner experiments after fixing stale ptool module reload/registration state in the orchestrator code.

## Scope

This rerun used the already-induced formulas-only and rules-only ptools, then ran the OrchestrationLearner with:

- Supervisor/big model: `gemini/gemini-3.1-pro-preview`
- Agent model: `gemini/gemini-3.1-flash-lite-preview`
- Dataset split: cached MedCalc train split
- Formulas categories: `dosage`, `lab test`, `physical`
- Rules categories: `diagnosis`, `risk`, `severity`
- Sampling target: about 4 cases/calculator for learner train and 2 cases/calculator for learner eval
- Reload fix commit already present before these runs: `503c3a0 Fix orchestrator ptools reload cleanup`

No edits were made to `src/secretagent/core.py`, `src/secretagent/implement/pydantic.py`, or `src/secretagent/implement/util.py` for these reruns.

## Commands

Formulas-only learner:

```bash
set -a; source ../../.env; set +a; HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 uv run python -m secretagent.cli.orchestration_learner run --config-file conf/induced_orch_formula.yaml --ptools-module ptools_induced_formula --scratch-evolved --n-train 132 --n-eval 66 --max-iterations 6 --supervisor-model gemini/gemini-3.1-pro-preview --custom-instructions "Preserve the SecretAgent interface shape. Do not emit config overrides that change ptools.*.method or ptools.*.fn. Do not convert the public calculate_medical_value entry point to a direct implementation unless the complete callable is present as a normal Python function. Prefer source-only changes to helper docstrings, helper logic, or additional uniquely named helper functions." evaluate.max_workers=4 llm.model=gemini/gemini-3.1-flash-lite-preview
```

Rules-only learner:

```bash
set -a; source ../../.env; set +a; HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 uv run python -m secretagent.cli.orchestration_learner run --config-file conf/induced_orch_rule.yaml --ptools-module ptools_induced_rule --scratch-evolved --n-train 76 --n-eval 38 --max-iterations 6 --supervisor-model gemini/gemini-3.1-pro-preview --custom-instructions "Preserve the SecretAgent interface shape. Do not emit config overrides that change ptools.*.method or ptools.*.fn. Do not convert the public calculate_medical_value entry point to a direct implementation unless the complete callable is present as a normal Python function. Prefer source-only changes to helper docstrings, helper logic, or additional uniquely named helper functions." evaluate.max_workers=4 llm.model=gemini/gemini-3.1-flash-lite-preview
```

The exact existing-benchmark evals were run as one-off fresh Python evaluators. They loaded the historical case lists from:

- Formulas: `benchmarks/results/medcalc/formulas/20260422.213053.react/results.csv`
- Rules: `benchmarks/results/medcalc/rules/20260422.213053.react/results.csv`

and evaluated the evolved ptools by setting `PYTHONPATH` to the learner run directory and overriding `ptools.calculate_medical_value.tool_module=ptools_evolved`.

## Artifacts

| Experiment | Learner run directory | Scratch ptools | Final benchmark directory |
|---|---|---|---|
| Formulas-only | `benchmarks/medcalc/results/orchestration_learner/20260430.172350.orch_learner/` | `benchmarks/medcalc/.orchestration_learner/ptools_induced_formula_20260430.172542_scratch.py` | `benchmarks/medcalc/results/benchmark_eval/20260501.083006.formula_orchfix_exact_existing_benchmark/` |
| Rules-only | `benchmarks/medcalc/results/orchestration_learner/20260501.041531.orch_learner/` | `benchmarks/medcalc/.orchestration_learner/ptools_induced_rule_20260501.041707_scratch.py` | `benchmarks/medcalc/results/benchmark_eval/20260501.083619.rule_orchfix_exact_existing_benchmark/` |

The full learner directories contain `report.json`, `report.html`, `implementation.yaml`, `run_metadata.json`, `ptools_evolved.py`, plots, final eval results, and per-iteration before/after source snapshots.

## Learner Results

| Experiment | Train sample | Eval sample | Best iteration | Best train accuracy | Final held-out eval accuracy | Supervisor cost |
|---|---:|---:|---:|---:|---:|---:|
| Formulas-only | 132 | 66 | 6 | 118/132 = 89.4% | 57/66 = 86.4% | $1.5864 |
| Rules-only | 76 | 38 | 2 | 45/76 = 59.2% | 22/38 = 57.9% | $1.9920 |

Formulas iteration summary:

| Iteration | Train accuracy | Held-out eval accuracy | Kept |
|---:|---:|---:|---|
| 0 | 97/132 = 73.5% | 49/66 = 74.2% | yes |
| 1 | 110/132 = 83.3% | 51/66 = 77.3% | yes |
| 2 | 109/132 = 82.6% | 53/66 = 80.3% | no |
| 3 | 110/132 = 83.3% | 58/66 = 87.9% | yes |
| 4 | 112/132 = 84.8% | 55/66 = 83.3% | yes |
| 5 | 113/132 = 85.6% | 53/66 = 80.3% | yes |
| 6 | 118/132 = 89.4% | 56/66 = 84.8% | yes |

Rules iteration summary:

| Iteration | Train accuracy | Held-out eval accuracy | Kept |
|---:|---:|---:|---|
| 0 | 33/76 = 43.4% | 17/38 = 44.7% | yes |
| 1 | not evaluated | not evaluated | no |
| 2 | 45/76 = 59.2% | 22/38 = 57.9% | yes |
| 3 | 39/76 = 51.3% | 24/38 = 63.2% | no |
| 4 | 44/76 = 57.9% | 27/38 = 71.1% | no |
| 5 | 39/76 = 51.3% | 23/38 = 60.5% | no |
| 6 | not evaluated | not evaluated | no |

## Existing Benchmark Results

These are the exact historical benchmark case lists, not the accidental all-train run and not the 99-case default stratified formulas eval.

| Experiment | Cases | Accuracy | Exact match | Total cost | Avg cost |
|---|---:|---:|---:|---:|---:|
| Formulas-only | 205 | 127/205 = 61.95% | 44.39% | $0.175376 | $0.000909 |
| Rules-only | 64 | 27/64 = 42.19% | 42.19% | $0.060446 | $0.000944 |

Formulas category breakdown:

| Category | Cases | Accuracy |
|---|---:|---:|
| dosage | 4 | 1/4 = 25.0% |
| lab test | 84 | 37/84 = 44.0% |
| physical | 117 | 89/117 = 76.1% |

Rules category breakdown:

| Category | Cases | Accuracy |
|---|---:|---:|
| diagnosis | 10 | 6/10 = 60.0% |
| risk | 46 | 19/46 = 41.3% |
| severity | 8 | 2/8 = 25.0% |

## Errors And Warnings Observed

The original same-process reload bug did not recur. Earlier runs had failed with duplicate ptool/tool registration after re-executing evolved modules in the same process. The orchestrator reload fix clears stale module globals and unregisters interfaces from the same module before re-exec, so these reruns did not show `Tool name conflicts with existing tool`.

Actual errors in the completed reruns:

- Rules learner iterations 1 and 6 produced invalid supervisor proposals and were rejected before train/eval. The terminal error was `reload failed: module, class, method, function, traceback, frame, or code object was expected, got Interface`. These were rollbacks, not run crashes.
- Rules learner baseline/train traces included request-limit validation loops where the agent failed to return a strict `float`: iter0 train had 3 `request_limit of 50` exceptions (`train.9524`, `train.9516`, `train.5888`) and iter0 eval had 2 (`train.4375`, `train.9509`).
- Rules iter2 train had 2 transient model/service exceptions: one Gemini server disconnect (`train.0779`) and one timeout (`train.4421`). Rules final held-out eval had no exceptions.
- Formulas iter6 held-out eval had 1 validation retry exception (`train.5191`), but the final held-out eval rerun had no exceptions.
- The exact formulas benchmark had 12 transient Gemini 503 `UNAVAILABLE` errors, all counted as incorrect. The affected cases were `train.7350`, `train.4314`, `train.6901`, `train.7472`, `train.5968`, `train.7448`, `train.4678`, `train.8384`, `train.3525`, `train.2627`, `train.2015`, and `train.5770`.
- The exact rules benchmark had no recorded exceptions.
- LiteLLM emitted async cleanup warnings after some runs, including pending-task and event-loop cleanup messages. These warnings did not abort the learner or benchmark evaluations.

Two non-final eval attempts should not be used as reported benchmark numbers:

- `benchmarks/medcalc/results/benchmark_eval/20260501.081904.formula_orchfix_existing_benchmark/` came from an accidental all-train evaluation and was interrupted.
- `benchmarks/medcalc/results/benchmark_eval/20260501.082512.formula_orchfix_existing_benchmark_3pc/` completed 99 cases, but that was the current default 3/calc stratified formulas sample, not the historical existing benchmark case list.

## Interpretation

The reload/registration bug is fixed for this workflow: the learner completed both formulas-only and rules-only reruns without duplicate ptool-name failures. The formulas learner improved its own held-out split substantially, but it did not transfer to the exact historical formulas benchmark. The rules learner kept one improvement on its learner split, but the exact historical rules benchmark also declined relative to the earlier 2026-04-30 induced/evolved baseline.

Treat the exact benchmark numbers above as the committed result for this rerun, and keep the 2026-04-30 numbers in `docs/medcalc_induction_report.md` as a separate historical baseline.
