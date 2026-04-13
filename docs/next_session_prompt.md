# Prompt for Next Session: Fix Population Optimizer and Get Real Accuracy Improvement

## Context

You are continuing work on the population-based pipeline optimization system for secretagent. The infrastructure was built in the previous session (46 commits, 316 tests pass) but **no accuracy improvement was achieved** on MedCalc-Bench. This session's goal: fix the identified bugs, implement the clean architectural vision, and demonstrate a real accuracy improvement.

**Read these files first** (in this order):
1. `CLAUDE.md` — project conventions
2. `docs/CLI.md` — how to run things
3. This document — the full bug list and vision

**Key constraint from the user:**
- NEVER do manual config sweeps. The meta-optimizer makes ALL decisions.
- Model is fixed to DeepSeek-V3.1 for testing. Don't add upgrade/downgrade to the transform list.
- Use 1/calc (55 cases) for quick tests. Only use 4/calc (220 cases) for the final showcase run.
- Make lots of small, human-style commits. No co-author lines.
- Editing `benchmarks/medcalc/` and `src/secretagent/orchestrate/` is fair game. Don't edit other core packages (`src/secretagent/core.py`, `src/secretagent/implement/`, `src/secretagent/record.py`, etc.).

---

## The Ideal Vision

The population optimizer should work like this:

```
1. COMPOSE: LLM generates initial pipeline code from ptool catalog
   → Pipeline object contains REAL Python code (not a thin delegate)
   → Code calls ptool interfaces: identify_calculator(), extract_values_with_context(), etc.

2. EVALUATE: Run pipeline on stratified minibatch
   → All ptool calls recorded via Interface.__call__
   → Per-case scores collected in candidate.instance_scores

3. SELECT: Instance-wise Pareto front
   → Candidates that are best on ANY case survive
   → Preserves specialist diversity

4. GUIDE: Meta-optimizer LLM sees population + profiles + operators
   → Proposes mutations with reasoning
   → Meta-optimizer is the SOLE authority (no should_apply gates)

5. MUTATE: Transforms generate NEW CODE via LLM + ruff fix + compile
   → Even "config" transforms (swap_strategy) should generate code
   → e.g., "replace LLM call to identify_calculator with Python regex + LLM fallback"
   → The _generate_code + ruff pipeline already exists in base.py

6. ACCEPT: Evaluate each mutated candidate with its own config
   → Save/restore global config around each evaluation
   → Populate instance_scores from results.jsonl per-case data

7. BUDGET: Track all costs, stop when exhausted
```

The key difference from what exists: **every mutation produces new pipeline code**, not just config flips. The code generation + ruff fix + compile pipeline already exists (`PipelineTransform._generate_code`). It just needs to be used by all transforms.

---

## Bugs to Fix (Priority Order)

### P0: Architectural (these prevent the system from working)

#### Bug 1: instance_scores is never populated
**File:** `src/secretagent/orchestrate/improve.py`, evaluation loop (~line 401-426)
**Problem:** `PipelineCandidate.instance_scores` is always empty. `pareto_front()` returns ALL candidates. Instance-wise Pareto selection is completely broken.
**Fix:** After evaluation, read `results.jsonl` and extract per-case `correct` scores:
```python
import json
jsonl_path = Path(new_dirs[0]) / 'results.jsonl'
if jsonl_path.exists():
    with open(jsonl_path) as f:
        for line in f:
            record = json.loads(line)
            case_name = record.get('case_name', '')
            c.instance_scores[case_name] = float(record.get('correct', 0))
```

#### Bug 2: Config not saved/restored between candidate evaluations
**File:** `src/secretagent/orchestrate/improve.py`, evaluation loop (~line 401-426)
**Problem:** Evaluating candidate A sets `llm.model=X` in global config. Candidate B then inherits A's config. Candidates are not evaluated independently.
**Fix:** Use `config.configuration()` context manager:
```python
from secretagent.config import configuration
for c in population.candidates:
    if c.profile is not None:
        continue
    with configuration(**{k: v for k, v in c.config.items()}):
        implement_via_config(ptools_mod, config.require('ptools'))
        new_dirs = run_eval_fn()
        c.profile = profile_from_results(new_dirs)
        # populate instance_scores here too
```
Note: `configuration()` takes kwargs, not dotlist. May need to convert dotlist to nested dict first, or add the config as a dotlist within the context.

#### Bug 3: Delegate Pipeline gives code transforms nothing to modify
**File:** `benchmarks/medcalc/run_population.py`, pipeline construction (~line 120-125)
**Problem:** The Pipeline is `return calculate_medical_value(patient_note, question)` — a thin wrapper. When LLM-based transforms (route, restructure, expand, induce) try to rewrite this, they produce garbage.
**Fix:** Use `method: orchestrate` for `calculate_medical_value`. The OrchestrateFactory generates real pipeline code from the ptool catalog. The conf/orchestrate.yaml already exists. BUT: the orchestrated pipeline starts at 62.9% (vs 80% hand-coded). To get the best of both worlds:
- Option A: Inject `pipeline_workflow` source into the Pipeline object manually (read the source at module level, not via inspect on the factory)
- Option B: Use orchestrate but give the LLM the hand-coded pipeline as a "reference implementation" in the compose prompt
- Option C: Start with orchestrate (62.9%) and rely on transforms to improve it past 80% over many iterations

### P1: Logic bugs (these cause wrong behavior)

#### Bug 4: should_apply gates override meta-optimizer
**Files:** All transform files in `src/secretagent/orchestrate/transforms/`
**Problem:** Transforms have hardcoded thresholds (`error_rate > 0.3`, `cost_fraction > 0.5`, etc.). The meta-optimizer proposes a mutation, but the transform's `should_apply()` rejects it silently.
**Fix:** In `_apply_mutation()` (improve.py), skip the `should_apply()` check when the mutation was proposed by the meta-optimizer. The meta-optimizer already considered the profile. Only use `should_apply()` for heuristic mode (when no meta-optimizer).

#### Bug 5: swap_strategy, upgrade, downgrade don't generate code
**Files:** `transforms/swap_strategy.py`, `transforms/upgrade.py`, `transforms/downgrade.py`
**Problem:** These return `new_config` dicts only. They flip a config switch but don't generate any new code. The pipeline code stays the same.
**Fix:** Rewrite these to use `_generate_code()`. For example, swap_strategy should:
1. Look at the ptool being swapped
2. Generate Python code that does the cheap thing (regex, lookup table) with LLM fallback
3. Compile into new pipeline code
4. Return `new_pipeline_code` instead of (or in addition to) `new_config`

Example for swap_strategy → direct with fallback:
```
Instruction to LLM:
"Replace the call to identify_calculator() with a Python implementation.
Use regex pattern matching on the question text for common calculators.
Fall back to identify_calculator() for unrecognized patterns.
This reduces cost while maintaining accuracy."
```

#### Bug 6: Route and induce produce broken code during seeding
**File:** `src/secretagent/orchestrate/improve.py`, `_seed_via_mutation()` (~line 524)
**Problem:** During seeding, transforms are applied to generate variants. But route and induce try to rewrite the delegate pipeline (`return calculate_medical_value(...)`) and produce nonsensical code that fails at 0% accuracy.
**Fix:** Only use config-only transforms for seeding, OR fix Bug 3 first so the Pipeline has real code.

#### Bug 7: Evolve uses only 20 hardcoded train cases
**File:** `benchmarks/medcalc/run_population.py`, line ~157
**Problem:** `t.train_cases = eval_dataset.cases[:20]` — hardcoded to 20 cases from the eval set. Too small for reliable fitness.
**Fix:** Make configurable. Use at least 50 cases. Draw from a separate train split, not the eval set.

### P2: Quality issues (these reduce effectiveness)

#### Bug 8: extract_values_with_context docstring doesn't explain the context format
**File:** `benchmarks/medcalc/ptools.py`, the `extract_values_with_context` interface definition
**Problem:** SimulateFactory builds prompts from the docstring. The docstring says "calculator-specific context" but doesn't explain the format. The actual context (built in `_extract_values_two_stage`) has detailed extraction instructions that the simulate prompt never sees.
**Fix:** Enrich the docstring with the expected format:
```python
@interface
def extract_values_with_context(patient_note: str, calculator_context: str) -> dict:
    """Extract clinical values using calculator-specific context.

    The calculator_context contains:
    - Calculator name and description
    - Required parameter names (use as exact JSON keys)
    - Optional reasoning from prior analysis (for scoring calculators)
    - Instructions for unit conversion, boolean handling, etc.

    Return {"extracted": {"param_name": value, ...}, "missing": [...]}
    """
```

#### Bug 9: Profiler tracks exceptions, not wrong answers
**File:** `src/secretagent/orchestrate/profiler.py`
**Problem:** `error_patterns` only captures outputs starting with `"**exception"`. Wrong answers (the main source of accuracy loss) have 0 errors. Transforms that trigger on `error_rate` miss the real problem.
**Note:** Can't edit profiler.py (core package). Workaround: the meta-optimizer prompt should explain that "0 errors" doesn't mean "0 accuracy problems" — profile accuracy vs error_rate are different metrics.

#### Bug 10: Pipeline namespace doesn't update when ptools are re-bound
**File:** `src/secretagent/orchestrate/improve.py`, `_apply_mutation()` and evaluation loop
**Problem:** When a candidate's config changes the method for a ptool, `implement_via_config()` re-binds the Interface object. But the Pipeline's `_fn.__globals__` still holds references to the old Interface state. This may not be an issue if Interfaces are mutable singletons (the Pipeline's reference to the Interface object stays valid even after re-binding). Verify this.

---

## Files to Read Before Starting

**Core architecture (read-only, don't modify):**
- `src/secretagent/core.py` — Interface, Implementation, Factory
- `src/secretagent/implement/core.py` — DirectFactory, SimulateFactory (note: SimulateFactory records calls, DirectFactory doesn't)
- `src/secretagent/record.py` — recorder context manager
- `src/secretagent/evaluate.py` — Evaluator base class
- `src/secretagent/config.py` — configuration() context manager

**Orchestration (modify freely):**
- `src/secretagent/orchestrate/improve.py` — the population loop (main file to fix)
- `src/secretagent/orchestrate/population.py` — PipelineCandidate, Population, Pareto front
- `src/secretagent/orchestrate/meta_optimizer.py` — MetaOptimizer
- `src/secretagent/orchestrate/budget.py` — BudgetTracker
- `src/secretagent/orchestrate/transforms/` — all 11 transforms
- `src/secretagent/orchestrate/transforms/base.py` — _generate_code + ruff pipeline
- `src/secretagent/orchestrate/prompt_templates/` — meta_guide.txt, compose.txt, transform_base.txt, crossover.txt
- `src/secretagent/orchestrate/models.yaml` — model catalog

**MedCalc benchmark (modify freely):**
- `benchmarks/medcalc/ptools.py` — interface definitions and pipeline_workflow
- `benchmarks/medcalc/run_population.py` — the optimizer runner
- `benchmarks/medcalc/conf/orchestrate.yaml` — orchestrate config
- `benchmarks/medcalc/conf/population.yaml` — direct pipeline config
- `benchmarks/medcalc/expt.py` — MedCalcEvaluator, setup(), load_dataset()

---

## Execution Plan

### Phase 1: Fix the plumbing (no API calls needed)
1. Fix Bug 1 (instance_scores) — ~10 lines in improve.py
2. Fix Bug 2 (config save/restore) — wrap evaluation in configuration() context
3. Fix Bug 4 (skip should_apply for meta-optimizer proposals) — ~5 lines in _apply_mutation
4. Fix Bug 7 (evolve train cases) — make configurable
5. Fix Bug 8 (docstring) — enrich extract_values_with_context
6. Run tests: `uv run python -m pytest tests/ -q`

### Phase 2: Make transforms generate code
7. Rewrite swap_strategy.apply() to use _generate_code — it should produce Python code that does the cheap thing + LLM fallback
8. Verify repair, route, restructure, expand, induce all work with real pipeline code
9. Run tests again

### Phase 3: Fix the Pipeline problem
10. Either inject pipeline_workflow source into Pipeline OR use orchestrate config
11. Test that code transforms can actually modify the pipeline

### Phase 4: Real API testing
12. Run with 1/calc, 5 iterations, verify transforms execute and accuracy changes
13. If accuracy improves, run final showcase: 4/calc, 15 iterations
14. Report: BASELINE → OPTIMIZED → FINAL numbers

### Phase 5: Code review
15. Run the elite-code-reviewer agent on all changes
16. Fix any issues found
17. Final commit

---

## Success Criteria

1. `instance_scores` is populated — `pareto_front()` returns a proper subset of candidates
2. Config is saved/restored — candidates are evaluated independently
3. At least one transform generates new pipeline code that improves accuracy
4. Final 4/calc evaluation shows accuracy > baseline (currently 78.9% with Qwen3.5-9B on reference, ~80% with V3.1)
5. All tests pass
6. Meta-optimizer proposals are the sole authority — no transform overrides them

---

## What NOT to Do

- Don't manually sweep model configurations
- Don't edit core packages (core.py, implement/, record.py, config.py, evaluate.py)
- Don't add Claude co-author lines to commits
- Don't skip the code reviewer at the end
- Don't run 4/calc evaluations until you have a confirmed improvement at 1/calc
- Don't hardcode model names — use models.yaml
- Don't add features beyond what's needed to fix the bugs and get accuracy improvement
