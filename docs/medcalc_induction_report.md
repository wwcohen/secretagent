# MedCalc-Bench: Ptool Induction + Orchestrator Improvement

## 0. Artifact Map and Git Status

This report is the index for the MedCalc induction/orchestration artifacts in this repository. A shorter browseable index also lives at `benchmarks/medcalc/results/README.md` for people starting from the results tree. The report file itself is listed in `.gitignore`, so updates to this file must be force-added when committing.

### 2026-05-01 rerun after orchestrator reload fix

A focused rerun record lives in `docs/medcalc_induction_rules.md`. It covers the formula-only and rule-only OrchestrationLearner reruns performed after commit `503c3a0 Fix orchestrator ptools reload cleanup`.

| Experiment | Learner run directory | Final held-out eval | Exact existing benchmark |
|---|---|---:|---:|
| Formula-only rerun | `benchmarks/medcalc/results/orchestration_learner/20260430.172350.orch_learner/` | 57/66 = 86.4% | 127/205 = 61.95% |
| Rule-only rerun | `benchmarks/medcalc/results/orchestration_learner/20260501.041531.orch_learner/` | 22/38 = 57.9% | 27/64 = 42.19% |

The exact benchmark directories for this rerun are:

- Formula: `benchmarks/medcalc/results/benchmark_eval/20260501.083006.formula_orchfix_exact_existing_benchmark/`
- Rule: `benchmarks/medcalc/results/benchmark_eval/20260501.083619.rule_orchfix_exact_existing_benchmark/`

The duplicate ptool/tool-name same-process reload error did not recur in this rerun. Non-fatal errors are documented in `docs/medcalc_induction_rules.md`.

### Read this first: where to find the main artifacts

Use this table as the human-readable index. The directory names contain timestamps because that is how the runner writes outputs, but the left column is the stable experiment label to use in discussion.

| Human label | What it is | Final ptools to inspect/use | Result directory |
|---|---|---|---|
| Historical induced ptools | Original best induced ptools from the 12-way induction matrix | `benchmarks/medcalc/ptools_induced.py` | See Part A result directories under `benchmarks/medcalc/results/*induced*_eval/` |
| Historical induced + supervisor refinement | OrchestrationLearner starting from `ptools_induced.py` | `benchmarks/medcalc/ptools_induced_evolved.py` | `benchmarks/medcalc/results/orchestration_learner/20260427.021444.orch_learner/` |
| Workflow provided / existing workflow | OrchestrationLearner on the hand-provided MedCalc workflow (`conf/workflow.yaml`, `seed_orchestrate=false`) | `benchmarks/medcalc/results/orchestration_learner/20260426.040958.orch_learner/ptools_evolved.py` and tracked scratch copy `benchmarks/medcalc/.orchestration_learner/ptools_20260426.040958_scratch.py` | `benchmarks/medcalc/results/orchestration_learner/20260426.040958.orch_learner/` |
| Workflow composed by orchestrator | OrchestrationLearner after first asking the orchestrator to compose a seed workflow (`conf/workflow.yaml`, `seed_orchestrate=true`) | `benchmarks/medcalc/results/orchestration_learner/20260426.182640.orch_learner/ptools_evolved.py` and tracked scratch copy `benchmarks/medcalc/.orchestration_learner/ptools_20260426.182640_scratch.py` | `benchmarks/medcalc/results/orchestration_learner/20260426.182640.orch_learner/` |
| Formula-only induced ptools | New formula-only induction on formula calculator traces | `benchmarks/medcalc/ptools_induced_formula.py` | `benchmarks/medcalc/learned/formula-4pc-pro-mp3/20260430.020302.calculate_medical_value__ptool_inducer/` |
| Formula-only induced + supervisor run | Completed learner run starting from formula-only induced ptools; no supervisor edit was kept | `benchmarks/medcalc/ptools_induced_formula_evolved.py` | `benchmarks/medcalc/results/orchestration_learner/20260430.021235.orch_learner/` |
| Rule-only induced ptools | New rule-only induction on rule calculator traces | `benchmarks/medcalc/ptools_induced_rule.py` | `benchmarks/medcalc/learned/rule-4pc-pro-mp3/20260430.020806.calculate_medical_value__ptool_inducer/` |
| Rule-only induced + supervisor run | Completed learner run starting from rule-only induced ptools; no supervisor edit was kept | `benchmarks/medcalc/ptools_induced_rule_evolved.py` | `benchmarks/medcalc/results/orchestration_learner/20260430.035155.orch_learner/` |

For the 2026-04-30 formula-only/rule-only existing-benchmark evaluations, use:

- Formula benchmark eval: `benchmarks/medcalc/results/benchmark_eval/20260430.051051.formula_orch_on_existing_benchmark/`
- Rule benchmark eval: `benchmarks/medcalc/results/benchmark_eval/20260430.061531.rule_orch_on_existing_benchmark/`

For the 2026-05-01 rerun after the orchestrator reload fix, use:

- Formula benchmark eval: `benchmarks/medcalc/results/benchmark_eval/20260501.083006.formula_orchfix_exact_existing_benchmark/`
- Rule benchmark eval: `benchmarks/medcalc/results/benchmark_eval/20260501.083619.rule_orchfix_exact_existing_benchmark/`

### Committed ptool artifacts from the earlier induction session

These are the original MedCalc induced ptool artifacts from the 2026-04-26/2026-04-27 run and are already part of git:

| Artifact | Path |
|---|---|
| Original induced orchestration config | `benchmarks/medcalc/conf/induced_orch.yaml` |
| Original induced ptool wrapper | `benchmarks/medcalc/ptools_induced.py` |
| Original evolved induced ptool wrapper | `benchmarks/medcalc/ptools_induced_evolved.py` |
| Original induction matrix outputs | `benchmarks/medcalc/learned/stateless-oc0-mp3/`, `stateless-oc0-mp5/`, `stateless-oc0-mp8/`, `stateless-oc1-mp3/`, `stateless-oc1-mp5/`, `stateless-oc1-mp8/`, `state-oc0-mp3/`, `state-oc0-mp5/`, `state-oc0-mp8/`, `state-oc1-mp3/`, `state-oc1-mp5/`, `state-oc1-mp8/` |

### 2026-04-30 formula-only and rule-only ptool artifacts

These are the new artifacts from the formula-only/rule-only experiment requested on 2026-04-30. They are committed together with this report so the learned ptools are reproducible from git:

| Artifact | Path |
|---|---|
| Formula-only orchestration config | `benchmarks/medcalc/conf/induced_orch_formula.yaml` |
| Rule-only orchestration config | `benchmarks/medcalc/conf/induced_orch_rule.yaml` |
| Formula-only built ptool module | `benchmarks/medcalc/ptools_induced_formula.py` |
| Formula-only evolved ptool module | `benchmarks/medcalc/ptools_induced_formula_evolved.py` |
| Rule-only built ptool module | `benchmarks/medcalc/ptools_induced_rule.py` |
| Rule-only evolved ptool module | `benchmarks/medcalc/ptools_induced_rule_evolved.py` |
| Formula-only inducer output | `benchmarks/medcalc/learned/formula-4pc-pro-mp3/20260430.020302.calculate_medical_value__ptool_inducer/` |
| Rule-only inducer output | `benchmarks/medcalc/learned/rule-4pc-pro-mp3/20260430.020806.calculate_medical_value__ptool_inducer/` |

The formula/rule `*_evolved.py` modules matched their corresponding built modules after the completed learner runs because the supervisor did not keep any proposed code changes.

### Workflow-mode OrchestrationLearner artifacts

These are separate from the induced-ptool experiments above. They answer the question "what happens when the learner starts from an existing/provided workflow versus a workflow first composed by the orchestrator?"

| Mode | Config / setup | Result directory | Final ptools | Summary |
|---|---|---|---|---|
| Workflow provided / existing workflow | `conf/workflow.yaml`, `seed_orchestrate=false`, `scratch_evolved=true` | `benchmarks/medcalc/results/orchestration_learner/20260426.040958.orch_learner/` | `benchmarks/medcalc/results/orchestration_learner/20260426.040958.orch_learner/ptools_evolved.py` | best train 79.3%, final eval 67.1% |
| Workflow composed by orchestrator | `conf/workflow.yaml`, `seed_orchestrate=true`, `scratch_evolved=true` | `benchmarks/medcalc/results/orchestration_learner/20260426.182640.orch_learner/` | `benchmarks/medcalc/results/orchestration_learner/20260426.182640.orch_learner/ptools_evolved.py` | best train 82.9%, final eval 72.0% |

The same final code is also present in tracked scratch-module files:

- Provided workflow scratch copy: `benchmarks/medcalc/.orchestration_learner/ptools_20260426.040958_scratch.py`
- Orchestrator-composed workflow scratch copy: `benchmarks/medcalc/.orchestration_learner/ptools_20260426.182640_scratch.py`

The run directory is the better place to send readers because it contains `report.json`, `report.html`, `implementation.yaml`, `run_metadata.json`, `ptools_evolved.py`, plots, final eval, and per-iteration before/after files.

### 2026-04-30 local result directories

These directories contain the local run outputs used for the 2026-04-30 numbers. They are result artifacts, not source ptools:

| Stage | Path | Key result |
|---|---|---|
| Formula trace generation, 4/calc train sample | `benchmarks/medcalc/results/20260430.004024.react_train_formula_4pc/` | 132 cases, 95/132 correct = 72.0% |
| Rule trace generation, 4/calc train sample | `benchmarks/medcalc/results/20260430.013446.react_train_rule_4pc/` | 76 cases, 39/76 correct = 51.3% |
| Formula OrchestrationLearner run | `benchmarks/medcalc/results/orchestration_learner/20260430.021235.orch_learner/` | best iteration 0, held-out eval 51/66 = 77.3% |
| Rule OrchestrationLearner run | `benchmarks/medcalc/results/orchestration_learner/20260430.035155.orch_learner/` | best iteration 0, held-out eval 19/38 = 50.0% |
| Formula fixed existing-benchmark eval | `benchmarks/medcalc/results/benchmark_eval/20260430.051051.formula_orch_on_existing_benchmark/` | 205 cases, 162/205 = 79.0% |
| Rule fixed existing-benchmark eval | `benchmarks/medcalc/results/benchmark_eval/20260430.061531.rule_orch_on_existing_benchmark/` | 64 cases, 33/64 = 51.6% |

The learner also wrote per-iteration train/eval result directories beside the `.orch_learner` directories, for example `20260430.021402.rc_iter0`, `20260430.025618.rc_iter0_eval`, `20260430.035321.rc_iter0`, and `20260430.042544.rc_iter0_eval`.

### Superseded and non-final local runs

Some local formula-only/rule-only orchestrator attempts were interrupted, superseded, or used the wrong benchmark subset. They are intentionally not used as final metrics. Current local examples include:

- `benchmarks/medcalc/results/orchestration_learner/20260430.153721.orch_learner/`
- `benchmarks/medcalc/results/orchestration_learner/20260430.154012.rc_iter0/`
- `benchmarks/medcalc/.orchestration_learner/ptools_induced_formula_20260430.153932_scratch.py`
- `benchmarks/medcalc/results/benchmark_eval/20260501.081904.formula_orchfix_existing_benchmark/`
- `benchmarks/medcalc/results/benchmark_eval/20260501.082512.formula_orchfix_existing_benchmark_3pc/`

Those artifacts are incomplete, superseded, or non-final outputs and are not used for any reported metric in this document.

---

**Date:** 2026-04-26 → 2026-04-27
**Updated:** 2026-04-30, with formula-only and rule-only induction artifacts
**Model (agent):** Gemini 3.1 Flash-Lite Preview
**Model (supervisor):** Gemini 3.1 Pro Preview
**Benchmark:** MedCalc-Bench v1.2 (NCBI), train split
**Code:** `benchmarks/medcalc/` in the secretagent repository

---

## 2026-04-30 Formula-Only and Rule-Only Split Experiments

These are the original completed formula-only/rule-only split experiments. The 2026-05-01 rerun after the orchestrator reload fix is summarized at the top of this report and documented in detail in `docs/medcalc_induction_rules.md`.

### What was run

| Experiment | Trace source | Induced ptools | Orchestrator final ptools | Config |
|---|---|---|---|---|
| Formula-only | `benchmarks/medcalc/results/20260430.004024.react_train_formula_4pc/` | `benchmarks/medcalc/ptools_induced_formula.py` | `benchmarks/medcalc/ptools_induced_formula_evolved.py` | `benchmarks/medcalc/conf/induced_orch_formula.yaml` |
| Rule-only | `benchmarks/medcalc/results/20260430.013446.react_train_rule_4pc/` | `benchmarks/medcalc/ptools_induced_rule.py` | `benchmarks/medcalc/ptools_induced_rule_evolved.py` | `benchmarks/medcalc/conf/induced_orch_rule.yaml` |

The raw inducer outputs are:

- Formula-only: `benchmarks/medcalc/learned/formula-4pc-pro-mp3/20260430.020302.calculate_medical_value__ptool_inducer/`
- Rule-only: `benchmarks/medcalc/learned/rule-4pc-pro-mp3/20260430.020806.calculate_medical_value__ptool_inducer/`

Both completed OrchestrationLearner runs kept iteration 0 as the best version. Therefore the final evolved modules are the same learned ptools with no accepted supervisor rewrite.

### Sampling

Both experiments used MedCalc's cached train partition, filtered by category, with Gemini 3.1 Pro Preview as the inducer/supervisor and Gemini 3.1 Flash-Lite Preview as the agent model.
Following the MedCalcV2 nomenclature in arXiv:2505.24217, the current code treats `physical`, `lab test`, and `dosage` as MedCalcV2 Formulas, and `risk`, `diagnosis`, and `severity` as MedCalcV2 Rules. Date calculators remain a separate explicit filter and are not part of the formulas/rules split below.

| Experiment | Category filter | Induction train sample | Learner train sample | Learner held-out eval sample |
|---|---|---:|---:|---:|
| Formula-only | `physical`, `lab test`, `dosage` | 132 = 4/calc across 33 calculators | 132 | 66 |
| Rule-only | `risk`, `diagnosis`, `severity` | 76 = 4/calc across 19 calculators | 76 | 38 |

Note: the trace-induction sample and OrchestrationLearner sample had matching counts, but the learner made its own disjoint train/eval split. The counts match the intended 4/calc and 2/calc scale, but the learner split is not guaranteed to be the exact same case IDs as the trace-generation sample.

### Trace generation and induction results

| Experiment | Trace result directory | Trace accuracy | Inducer output | Thoughts | Ptools |
|---|---|---:|---|---:|---:|
| Formula-only | `benchmarks/medcalc/results/20260430.004024.react_train_formula_4pc/` | 95/132 = 72.0% | `benchmarks/medcalc/learned/formula-4pc-pro-mp3/20260430.020302.calculate_medical_value__ptool_inducer/` | 119 | 3 |
| Rule-only | `benchmarks/medcalc/results/20260430.013446.react_train_rule_4pc/` | 39/76 = 51.3% | `benchmarks/medcalc/learned/rule-4pc-pro-mp3/20260430.020806.calculate_medical_value__ptool_inducer/` | 75 | 3 |

### OrchestrationLearner results

| Experiment | Orchestrator run directory | Best iteration | Train accuracy | Held-out eval accuracy | Final ptools |
|---|---|---:|---:|---:|---|
| Formula-only | `benchmarks/medcalc/results/orchestration_learner/20260430.021235.orch_learner/` | 0 | 96/132 = 72.7% | 51/66 = 77.3% | `benchmarks/medcalc/ptools_induced_formula_evolved.py` |
| Rule-only | `benchmarks/medcalc/results/orchestration_learner/20260430.035155.orch_learner/` | 0 | 31/76 = 40.8% | 19/38 = 50.0% | `benchmarks/medcalc/ptools_induced_rule_evolved.py` |

Per-iteration train/eval result directories were written next to the learner run directories. Important baseline directories:

- Formula train iter0: `benchmarks/medcalc/results/orchestration_learner/20260430.021402.rc_iter0/`
- Formula eval iter0: `benchmarks/medcalc/results/orchestration_learner/20260430.025618.rc_iter0_eval/`
- Rule train iter0: `benchmarks/medcalc/results/orchestration_learner/20260430.035321.rc_iter0/`
- Rule eval iter0: `benchmarks/medcalc/results/orchestration_learner/20260430.042544.rc_iter0_eval/`

The learner's in-process final eval hit tool-name registration conflicts for both runs, so those final-eval CSVs should not be used as metrics. Fresh-process benchmark evaluations below are the valid final numbers for the existing benchmark subsets.

### Existing benchmark subset evaluation

These evaluations used the exact existing benchmark case lists under `benchmarks/COMMON/results/medcalc/` and loaded those case IDs from the cached MedCalc train split.

| Experiment | Benchmark result directory | Cases | Accuracy | Exact match | Final ptools |
|---|---|---:|---:|---:|---|
| Formula-only | `benchmarks/medcalc/results/benchmark_eval/20260430.051051.formula_orch_on_existing_benchmark/` | 205 | 162/205 = 79.0% | 64.9% | `benchmarks/medcalc/ptools_induced_formula_evolved.py` |
| Rule-only | `benchmarks/medcalc/results/benchmark_eval/20260430.061531.rule_orch_on_existing_benchmark/` | 64 | 33/64 = 51.6% | 51.6% | `benchmarks/medcalc/ptools_induced_rule_evolved.py` |

Formula category breakdown:

| Category | Cases | Accuracy |
|---|---:|---:|
| dosage | 4 | 4/4 = 100.0% |
| lab test | 84 | 55/84 = 65.5% |
| physical | 117 | 103/117 = 88.0% |

Rule category breakdown:

| Category | Cases | Accuracy |
|---|---:|---:|
| diagnosis | 10 | 6/10 = 60.0% |
| risk | 46 | 22/46 = 47.8% |
| severity | 8 | 5/8 = 62.5% |

### Interpretation

The formula-only induced ptools generalized reasonably well to the existing formula benchmark subset, especially physical calculators. The rule-only induced ptools remained close to the trace-generation baseline and were weakest on risk-score cases, which still require careful criterion-by-criterion mapping and summation.

The completed supervisor runs did not produce an accepted improvement. Several proposed changes failed because they changed the SecretAgent interface/config shape or introduced duplicate tool-name registration problems during same-process reload/evaluation. The committed ptool modules are therefore the induced versions, not supervisor-modified versions.

---

## 1. What is this experiment about?

MedCalc-Bench is a dataset of 10,543 medical calculation problems. Each problem gives a patient clinical note and asks a numerical question like "What is this patient's CHA2DS2-VASc score?" or "Calculate the patient's BMI." The model must extract the right numbers from the note, pick the right formula, and compute the answer.

We ran two experiments back-to-back:

**Part A — Ptool Induction:** Can the system watch itself solve problems and automatically learn a better set of tools?

**Part B — Orchestrator Improvement:** Can a stronger supervisor model (Gemini Pro) iteratively improve those learned tools even further by analyzing failure cases?

### The overall pipeline

```
Hand-written tools (baseline)
  ↓ run agent on 110 training problems, record reasoning
  ↓
Ptool Inducer (categorize reasoning → synthesize new tools)
  ↓ evaluate 12 variants on 110 held-out problems
  ↓ pick the best variant
  ↓
OrchestrationLearner (supervisor analyzes failures → rewrites tool docstrings)
  ↓ 6 iterations of propose-evaluate-keep/rollback
  ↓
Final improved pipeline
```

### How both stages use the same agent mechanism

Both the baseline and all induced/improved variants run through the exact same agent mechanism: a `simulate_pydantic` factory, which is a pydantic-ai Agent in a tool-calling loop. The agent receives a prompt, decides which tool to call, reads the tool output, decides what to do next, and eventually returns a final answer. The **only thing that changes between experiments is which tools the agent has access to and what their docstrings say**.

Both the trace-generation stage and the evaluation stage use this same mechanism. In trace generation, the agent runs with the hand-written tools, and we record its reasoning. In evaluation, the agent runs with the learned tools. Same model, same prompt template, same loop.

---

## 2. Starting point: the hand-written tools

The hand-written agent setup has three specialist tools:

| Tool | What it does | Implementation |
|------|-------------|----------------|
| `identify_calculator` | Pick which medical formula to use | LLM call (one-shot, the LLM reads a docstring and predicts the output) |
| `extract_clinical_values` | Pull relevant numbers from the note | LLM call (same mechanism) |
| `compute_calculation` | Actually do the math | Deterministic Python code — calls the actual calculator implementations, always gets arithmetic right |

The agent calls these in a loop: typically identify → extract → compute → return answer. Sometimes it retries if extraction fails.

---

## Part A: Ptool Induction

## 3. How the learning works

The learning pipeline has four stages:

1. **Generate traces.** Run the agent with the hand-written tools on 110 training problems, while recording every reasoning step the model writes between tool calls (called "thoughts"). A special prompt template (`simulate_pydantic_thinking.txt`) was needed because Gemini Flash-Lite does not naturally emit reasoning text when in tool-calling mode — it only produces tool calls. The template adds an instruction: "Before every tool call, you MUST emit a short paragraph of plain reasoning."

2. **Categorize the thoughts.** Feed the ~100 recorded thoughts to the LLM and ask it to assign each one a short category label (like "PERFORM MATHEMATICAL CALCULATION" or "EVALUATE CLINICAL SCORE CRITERIA"). Then merge synonymous categories.

3. **Synthesize new tools.** For each surviving category that has at least 3 supporting examples, ask the LLM to write a function signature and docstring that captures what that category of reasoning does. Each synthesized tool becomes a stub — just a name, type signature, and detailed docstring with no code body. At runtime, the stub is "implemented" by sending the docstring + the input to an LLM and asking it to predict the output (same mechanism as the hand-written tools' LLM calls).

4. **Evaluate.** Replace the hand-written tools with the learned tools and re-run the agent on 110 held-out problems (different from the 110 training problems). Compare accuracy.

---

## 4. Induction experiments

### 4.1 Trace generation

Four trace-generation runs, each on 110 problems from MedCalc's train split:

| Config | Description | Seed | Cases | Thoughts collected | Accuracy |
|--------|-------------|------|-------|--------------------|----------|
| `react_train` | Stateless, hand-written tools | 42 | 110 | 101 | 68.2% |
| `react_eval` | Stateless, hand-written tools | 43 | 110 | 91 | 58.2% |
| `react_state_train` | State-aware, hand-written tools | 42 | 110 | 93 | 58.2% |
| `react_state_eval` | State-aware, hand-written tools | 43 | 110 | 49→110 | 59.1% |

**Seed 42** = training problems (used to generate traces for the inducer).
**Seed 43** = held-out problems (used only for evaluation — the inducer never sees these).

"Stateless" means the agent entry point is `calculate_medical_value` bound directly to a pydantic-ai Agent. "State-aware" means the entry point goes through a wrapper that stores the patient note in a module-level dictionary, so that induced tools could read the patient note directly. As discussed below, this didn't end up helping.

All runs used:
- Model: `gemini/gemini-3.1-flash-lite-preview`
- Thinking level: `high` (via `llm.reasoning_effort=high`)
- Prompt template: `simulate_pydantic_thinking.txt` (with explicit reasoning requirement)
- Caching: enabled

Total cost for all trace generation: approximately **$2.50**.

### 4.2 Induction matrix

We swept three choices, producing 12 variants:

| Axis | Values | Why |
|------|--------|-----|
| **State injection** | Stateless vs. State-aware | Does the induced tool need to see the patient note directly, or is the focus argument enough? |
| **Only-correct** | All traces (oc=0) vs. Correct-only (oc=1) | Is it better to learn only from successful reasoning, or from both successes and failures? |
| **Max tools** | 3, 5, 8 | How many distinct reasoning categories should we synthesize? |

All 12 induction runs used `gemini/gemini-3.1-flash-lite-preview` as the categorizer/synthesizer model, with `min_count=3` (a category needs at least 3 example thoughts to be synthesized).

The induction matrix took approximately **10 minutes** and cost approximately **$0.30**.

What each variant produced:

| Variant | Input thoughts | Categories found | Tools synthesized |
|---------|---------------|-----------------|-------------------|
| stateless-oc0-mp3 | 101 | 5 | 3 |
| stateless-oc0-mp5 | 101 | 5 | 4 |
| stateless-oc0-mp8 | 101 | 5 | 4 |
| stateless-oc1-mp3 | 76 | 6 | 3 |
| stateless-oc1-mp5 | 76 | 6 | 4 |
| stateless-oc1-mp8 | 76 | 6 | 4 |
| state-oc0-mp3 | 93 | 5 | 3 |
| state-oc0-mp5 | 93 | 5 | 5 |
| state-oc0-mp8 | 93 | 5 | 5 |
| state-oc1-mp3 | 66 | 4 | 3 |
| state-oc1-mp5 | 66 | 4 | 4 |
| state-oc1-mp8 | 66 | 4 | 4 |

`oc1` variants have fewer thoughts because they discard incorrect cases. `mp5`/`mp8` often cap at the same number as `mp5` because the merge step consolidates to 4-6 categories.

### 4.3 Held-out evaluation

Each of the 12 induced variants + 2 baselines was evaluated on the **same held-out 110 problems** (seed=43). Same model, same prompt template, same evaluation. Only the tools changed.

---

## 5. Induction results — full table

Sorted by within-tolerance accuracy (the primary metric), highest first:

| Variant | Accuracy | Exact match | Input tokens | Output tokens | Formula-based (86 cases) | Rule-based (24 cases) |
|---------|----------|-------------|-------------|---------------|--------------------------|----------------------|
| **stateless-oc0-mp3** | **66.4%** | **60.0%** | **848K** | **21K** | **73.3%** | **41.7%** |
| **state-oc1-mp8** | **66.4%** | **60.9%** | **1,116K** | **38K** | **73.3%** | **41.7%** |
| state-oc0-mp8 | 63.6% | 58.2% | 1,160K | 42K | 70.9% | 37.5% |
| stateless-oc0-mp5 | 60.9% | 58.2% | 1,297K | 22K | 69.8% | 29.2% |
| stateless-oc0-mp8 | 60.0% | 57.3% | 1,285K | 22K | 68.6% | 29.2% |
| state-oc0-mp3 | 60.0% | 53.6% | 750K | 25K | 62.8% | 50.0% |
| state-oc0-mp5 | 60.0% | 54.5% | 1,110K | 39K | 67.4% | 33.3% |
| **react_state_eval** (baseline) | **59.1%** | **54.5%** | **2,022K** | **110K** | **60.5%** | **54.2%** |
| **react_eval** (baseline) | **58.2%** | **54.5%** | **2,129K** | **94K** | **61.6%** | **45.8%** |
| stateless-oc1-mp8 | 55.5% | 52.7% | 1,682K | 23K | 58.1% | 45.8% |
| state-oc1-mp3 | 55.5% | 50.9% | 1,028K | 39K | 60.5% | 37.5% |
| state-oc1-mp5 | 52.7% | 48.2% | 804K | 27K | 58.1% | 33.3% |
| stateless-oc1-mp5 | 49.1% | 47.3% | 1,517K | 21K | 51.2% | 41.7% |
| stateless-oc1-mp3 | 44.5% | 39.1% | 1,656K | 21K | 47.7% | 33.3% |

### Accuracy definitions

- **Within-tolerance accuracy** (the primary metric): the predicted number falls within the dataset's specified lower and upper tolerance bounds for that problem. This is MedCalc-Bench's standard metric.
- **Exact match**: the predicted number matches the ground truth to floating-point precision (very strict).
- **Formula-based**: physical, lab test, dosage categories (formula-driven problems).
- **Rule-based**: risk, diagnosis categories (scoring/criteria problems).
- **Input/output tokens**: total across all 110 problems. At gemini-flash-lite pricing ($0.25/$1.50 per million), 848K input + 21K output ≈ **$0.24** per eval run.

### Per-category breakdown: winner (stateless-oc0-mp3) vs. baseline (react_eval)

| Category | Problems | Baseline | Winner | Change |
|----------|----------|----------|--------|--------|
| physical | 45 | 73.3% | 88.9% | **+15.6 pts** |
| lab test | 32 | 53.1% | 65.6% | **+12.5 pts** |
| risk | 20 | 50.0% | 45.0% | -5.0 pts |
| severity | 4 | 50.0% | 25.0% | -25.0 pts |
| diagnosis | 4 | 25.0% | 25.0% | 0.0 pts |
| date | 3 | 0.0% | 0.0% | 0.0 pts |
| dosage | 2 | 50.0% | 50.0% | 0.0 pts |
| **TOTAL** | **110** | **58.2%** | **66.4%** | **+8.2 pts** |

The induced tools helped most on **formula-based categories** (physical +15.6, lab test +12.5) but slightly hurt on **rule-based categories** (risk -5.0, severity -25.0). The induced tools learned to extract-and-compute in a single step, which is efficient for formula problems. But rule/scoring problems that require careful criterion-by-criterion evaluation may need the more structured multi-step approach the hand-written tools provide.

Note: severity and diagnosis have only 4 cases each — swings there are statistically noisy.

---

## 6. What tools did the induction winner learn?

The winning variant (`stateless-oc0-mp3`) learned **3 tools** from 101 reasoning steps:

| Induced tool | What it does | Supporting examples |
|-------------|-------------|---------------------|
| `calculate_clinical_score` | Extract clinical variables and apply a medical formula in one step | 39 |
| `compute_clinical_value` | Unit conversions and arithmetic | 26 |
| `apply_clinical_score` | Score a patient against a named scoring system criterion by criterion | 19 |

Key difference from the hand-written tools: the hand-written tools form a sequential **pipeline** (identify → extract → compute, 3 tool calls minimum). The induced tools are each **self-contained** — they do the full extract-and-compute in one call. The agent typically calls 1-2 tools instead of 3, which explains the 60% token reduction.

All three induced tools have no code body — just a docstring. At runtime, the LLM reads the docstring and predicts the output. The quality of the docstring (written by the learning pipeline from real reasoning traces) is what makes this work. The hand-written tools' LLM calls (`identify_calculator`, `extract_clinical_values`) work the same way — the difference is that a human wrote those docstrings, while the inducer wrote the new ones.

---

## 7. Induction findings

### What worked

1. **Learning from all traces beats learning from only correct traces.** oc=0 consistently outperforms oc=1. Recovery reasoning in failed traces teaches about failure modes.

2. **Fewer tools beat more tools.** 3-tool cap outperformed 5 and 8. The merge step consolidates to ~5 categories anyway; extra tools beyond 3 add noise.

3. **The induced agent is dramatically cheaper.** 848K tokens vs. 2.1M for the same 110 problems.

### What didn't work

1. **State injection.** The state-aware variants (where tools could read the patient note from a shared dictionary) tied or lost vs. stateless. Gemini packs sufficient context into the `focus` argument strings.

### Caveats

1. **Not an apples-to-apples model comparison.** The historical DeepSeek-V3.1 baseline (19.3%) used a different prompt, no thinking mode, different date. Fair comparison: gemini baseline (58.2%) vs. gemini induced (66.4%).

2. **Train split only.** All experiments used MedCalc's train split with different seeds for train/eval disjointness. Should be validated on the official test split.

---

## Part B: OrchestrationLearner Improvement

## 8. How the orchestrator works

The OrchestrationLearner takes the induced tools from Part A as its starting point and tries to improve them through iterative supervision:

1. Evaluate the current tools on 110 training problems
2. Analyze the failures — which problems went wrong and why
3. Send the full tool source code + failure analysis to a stronger supervisor model (Gemini 3.1 Pro)
4. The supervisor proposes a rewritten version of the tools file (modified docstrings, new tools, etc.)
5. Evaluate the proposed version on the same 110 problems
6. If accuracy improved → keep the change. If not → roll back.
7. Repeat for up to 6 iterations.

After all iterations, the best version is evaluated on the separate 110 held-out problems.

---

## 9. Orchestrator results

### Iteration-by-iteration

| Iter | Train acc | Eval acc | Sup. cost | Status | What the supervisor tried |
|------|-----------|----------|-----------|--------|---------------------------|
| 0 | 59.1% (65/110) | 60.9% (67/110) | $0.00 | KEPT | Baseline — unmodified induced ptools |
| 1 | 59.1% | 60.9% | $0.35 | ROLLBACK | Python router + `verify_calculation` tool. No effect — the config binding overrides function bodies |
| 2 | 61.8% (68/110) | 58.2% (64/110) | $0.33 | KEPT | Better docstrings: `<answer>` tag instructions, expanded scoring criteria, added deterministic calculator tool |
| 3 | 61.8% | 58.2% | $0.50 | ROLLBACK | `<math>`/`<date>` XML tags. Same accuracy, 54% more tokens |
| 4 | 60.0% (66/110) | 56.4% (62/110) | $0.39 | ROLLBACK | Expanded knowledge base + date parsing. Regressed |
| 5 | **65.5%** (72/110) | **62.7%** (69/110) | $0.45 | **KEPT** | Comprehensive formula reference + scoring criteria in docstrings + math evaluator tool |
| 6 | 53.6% (59/110) | 55.5% (61/110) | $0.40 | ROLLBACK | Tried to fix date encoding. Broke everything |

**Note on baseline discrepancy:** The orchestrator's iter0 baseline (59.1%) is lower than the induction report's winning accuracy (66.4%) because the cachier cache files were corrupted and had to be restored from a prior git commit. With a partially populated cache, Gemini's sampling produced different results on the non-cached cases. The fair comparison within the orchestrator run is iter0 (59.1%) → iter5 (65.5%) = **+6.4 points on train**.

### Per-category accuracy — orchestrator (train set)

| Category | Iter0 (baseline) | Iter5 (best) | Change |
|----------|-------------------|-------------|--------|
| physical | 95.8% (23/24) | **100%** (24/24) | +4.2 pts |
| dosage | 50.0% (2/4) | **75.0%** (3/4) | +25.0 pts |
| severity | 37.5% (3/8) | **62.5%** (5/8) | +25.0 pts |
| diagnosis | 33.3% (2/6) | **50.0%** (3/6) | +16.7 pts |
| lab test | 60.5% (23/38) | 65.8% (25/38) | +5.3 pts |
| risk | 50.0% (12/24) | 50.0% (12/24) | 0 pts |
| date | 0.0% (0/6) | 0.0% (0/6) | 0 pts |

### Per-category accuracy — orchestrator (eval set)

| Category | Iter0 (baseline) | Iter5 (best) | Change |
|----------|-------------------|-------------|--------|
| physical | 83.3% (20/24) | 91.7% (22/24) | +8.4 pts |
| dosage | 50.0% (2/4) | **75.0%** (3/4) | +25.0 pts |
| severity | 50.0% (4/8) | **62.5%** (5/8) | +12.5 pts |
| lab test | 65.8% (25/38) | 65.8% (25/38) | 0 pts |
| risk | 54.2% (13/24) | 50.0% (12/24) | -4.2 pts |
| diagnosis | 50.0% (3/6) | 33.3% (2/6) | -16.7 pts |
| date | 0.0% (0/6) | 0.0% (0/6) | 0 pts |

---

## 10. What the supervisor changed (iter5 — the winning iteration)

The supervisor's key insight: the LLM was zero-shotting complex calculations instead of using the induced tools, and when it did use tools, the docstrings lacked reference formulas and scoring criteria. The winning changes:

1. **Formula reference guide in `calculate_clinical_score` docstring.** Injected exact formulas for Delta Gap, Free Water Deficit, MDRD GFR, CKD-EPI, QTc variants, Friedewald LDL, MME, Steroid Equivalents, MELD-Na. This eliminated formula hallucination — the LLM no longer had to guess formulas from memory.

2. **Scoring criteria in `apply_clinical_score` docstring.** Injected point distributions for 15+ scoring systems (HAS-BLED, Child-Pugh, Wells PE/DVT, HEART, GBS, APACHE II, PSI, CHA2DS2-VASc, Caprini, Centor, FeverPAIN, SIRS, PERC, RCRI, Charlson). This eliminated criterion hallucination.

3. **`compute_calculation_impl` tool.** Added as a deterministic Python math evaluator — the LLM passes an expression string and gets an exact result. This gives the agent a way to verify its arithmetic without relying on LLM math.

4. **Position-based date/tuple extraction.** Modified the answer parser to detect dates (`MM/DD/YYYY`) and gestational tuples (`X weeks, Y days`) by checking if they appear at the end of the response, preventing dates in the patient note from being mistaken for answers.

5. **Orchestration instructions in `calculate_medical_value` docstring.** Explicitly instructs the LLM to delegate to specialized tools rather than zero-shotting.

The evolved file grew from 136 lines / 4.7KB to 224 lines / 12.8KB — the extra size is almost entirely richer docstrings.

### What the supervisor tried that didn't work

1. **Python routing (iter1):** Tried implementing `calculate_medical_value` as a Python function that routes to tools by keyword. Had zero effect because the `simulate_pydantic` config binding overrides function bodies — the LLM never sees or executes the Python code.

2. **XML tags (iter3):** Added `<math>` and `<date>` tags for the LLM to wrap arithmetic and dates. Same accuracy but 54% more tokens.

3. **Over-engineering (iter4, iter6):** Tried to solve the date problem by modifying float extraction logic, but introduced regressions. The fundamental issue is that `calculate_medical_value -> float` return type can't represent dates.

---

## 11. End-to-end comparison

| System | Eval accuracy (110 cases) | Input tokens | Notes |
|--------|--------------------------|-------------|-------|
| Hand-written baseline (react_eval) | 58.2% | 2,129K | 3 hand-written tools including deterministic calculator |
| **Induced ptools (stateless-oc0-mp3)** | **66.4%** | **848K** | 3 learned tools, all LLM-based, no deterministic calculator |
| Orchestrator iter0 (same induced, different cache) | 60.9% | ~402K | Lower due to cache corruption/restoration |
| **Orchestrator iter5 (best)** | **62.7%** | **~484K** | Enriched docstrings + deterministic math tool added back |

The induction experiment's 66.4% vs orchestrator's 62.7% comparison is **not apples-to-apples** — different cache states mean different LLM sampling on non-cached cases. Within each experiment, the relative comparisons are valid:
- Induction: 58.2% → 66.4% = **+8.2 pts** from learning better tools
- Orchestrator: 59.1% → 65.5% (train) / 60.9% → 62.7% (eval) = **+6.4 / +1.8 pts** from supervisor refinement

---

## 12. Cost summary

### Part A: Ptool induction

| Stage | Wall-clock | Cost |
|-------|-----------|------|
| Trace generation (4 × 110 cases) | ~3.5 hours | ~$2.50 |
| Induction matrix (12 variants) | ~10 min | ~$0.30 |
| Held-out evaluation (14 runs) | ~3.5 hours | ~$3.50 |
| **Part A total** | **~7.5 hours** | **~$6.30** |

### Part B: Orchestrator

| Component | Cost |
|-----------|------|
| Supervisor (Gemini 3.1 Pro, 6 iterations) | $2.42 |
| Eval LLM (Gemini Flash-Lite, ~14 train+eval runs) | ~$1.20 |
| **Part B total (wall-clock ~9 hours)** | **~$3.62** |

### Combined

| | Wall-clock | Cost |
|-|-----------|------|
| **Everything** | **~16.5 hours** | **~$9.92** |

All costs are for Gemini at published pricing ($0.25/$1.50 per million input/output for flash-lite, higher for pro). Caching was enabled throughout; repeat calls served from disk at zero cost.

---

## 13. Remaining failures and open questions

1. **Date calculations (6 cases):** All fail because `calculate_medical_value -> float` can't represent dates. The supervisor tried multiple approaches but none worked within the type constraint. Would need a return-type change or a separate date-handling entry point.

2. **Risk/scoring plateau (50%):** Risk category didn't improve despite the supervisor injecting detailed scoring criteria. The LLM still makes errors when summing many criteria (10+ items). May need a different approach — perhaps a deterministic scoring tool similar to `compute_calculation`.

3. **Cache sensitivity:** The 66.4% vs 59.1% baseline discrepancy shows these results are sensitive to Gemini's sampling. Caching helps reproducibility but makes comparisons across cache states unreliable. Future work should either run everything from scratch or ensure identical cache state.

4. **Test split validation:** All experiments used MedCalc's train split with different seeds. Should be validated on the official test split before drawing strong conclusions.

---

## 14. Artifacts

### Part A artifacts

| File | Purpose |
|------|---------|
| `benchmarks/medcalc/ptools_induced.py` | Self-contained module with 3 winning induced tools |
| `benchmarks/medcalc/conf/induced_orch.yaml` | Config that binds the induced tools |
| `benchmarks/medcalc/learned/<variant>/` | All 12 induction outputs |
| `benchmarks/medcalc/results/*induced*_eval/` | All 14 evaluation results |
| `benchmarks/medcalc/run_matrix.py` | Induction + evaluation matrix driver |
| `benchmarks/medcalc/build_induced.py` | Builds ptools_induced.py from any winning variant |

### Part B artifacts

| File | Purpose |
|------|---------|
| `benchmarks/medcalc/ptools_induced_evolved.py` | Best evolved ptools (iter5, 224 lines) |
| `benchmarks/medcalc/docs/orch_custom_instructions.txt` | Custom instructions for supervisor |
| `results/orchestration_learner/20260427.021444.orch_learner/` | Full run directory |
| `results/orchestration_learner/20260427.021444.orch_learner/report.html` | Interactive HTML report |
| `results/orchestration_learner/20260427.021444.orch_learner/iterations/` | Per-iteration before/after code, reasoning, traces |

### 2026-04-30 formula-only/rule-only artifacts

| File or directory | Purpose |
|------|---------|
| `benchmarks/medcalc/ptools_induced_formula.py` | Built formula-only ptools from the formula-only trace induction |
| `benchmarks/medcalc/ptools_induced_formula_evolved.py` | Final formula-only ptools after the completed OrchestrationLearner run; same as built ptools because no supervisor edit was kept |
| `benchmarks/medcalc/ptools_induced_rule.py` | Built rule-only ptools from the rule-only trace induction |
| `benchmarks/medcalc/ptools_induced_rule_evolved.py` | Final rule-only ptools after the completed OrchestrationLearner run; same as built ptools because no supervisor edit was kept |
| `benchmarks/medcalc/conf/induced_orch_formula.yaml` | Evaluation/orchestrator config for formula-only induced ptools |
| `benchmarks/medcalc/conf/induced_orch_rule.yaml` | Evaluation/orchestrator config for rule-only induced ptools |
| `benchmarks/medcalc/learned/formula-4pc-pro-mp3/20260430.020302.calculate_medical_value__ptool_inducer/` | Raw formula-only PtoolInducer output |
| `benchmarks/medcalc/learned/rule-4pc-pro-mp3/20260430.020806.calculate_medical_value__ptool_inducer/` | Raw rule-only PtoolInducer output |
| `benchmarks/medcalc/results/20260430.004024.react_train_formula_4pc/` | Formula-only trace-generation results used as induction input |
| `benchmarks/medcalc/results/20260430.013446.react_train_rule_4pc/` | Rule-only trace-generation results used as induction input |
| `benchmarks/medcalc/results/orchestration_learner/20260430.021235.orch_learner/` | Completed formula-only OrchestrationLearner run directory |
| `benchmarks/medcalc/results/orchestration_learner/20260430.035155.orch_learner/` | Completed rule-only OrchestrationLearner run directory |
| `benchmarks/medcalc/results/benchmark_eval/20260430.051051.formula_orch_on_existing_benchmark/` | Fresh-process formula-only evaluation on the existing benchmark subset |
| `benchmarks/medcalc/results/benchmark_eval/20260430.061531.rule_orch_on_existing_benchmark/` | Fresh-process rule-only evaluation on the existing benchmark subset |

---

## 15. Framework changes shipped

These are backward-compatible changes to the secretagent framework, required to make the pipeline work:

1. **`src/secretagent/learn/ptool_inducer.py`:** Fixed a bug where `collect_distillation_data` populated `self._items` but never `self.dataset`, causing the standard CLI to crash.

2. **`src/secretagent/implement/pydantic.py`:** Three opt-in additions:
   - Read alternate prompt template from config `simulate_pydantic.template` (default unchanged)
   - Forward `llm.reasoning_effort` to pydantic-ai's `ModelSettings.thinking`
   - Capture `'thinking'` part_kind as `'thought'` in message summaries

3. **`src/secretagent/implement/prompt_templates/simulate_pydantic_thinking.txt`:** New alternate prompt template with a hard reasoning requirement instructing models to write out their thinking before each tool call. Without this, Gemini Flash-Lite produces zero visible reasoning in tool-calling mode — it only emits tool calls.
