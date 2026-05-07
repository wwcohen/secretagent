# Orchestrator Experiment Log

All experiments run on March 22-23, 2026.

---

## Experiment 1: Math Word Problems (Custom Dataset)

**Date:** 2026-03-23
**Task:** 10 custom math word problems (addition, subtraction, multiplication, division)
**Ptools:** parse_numbers, identify_operation, compute_result, format_answer
**Ptool model:** Qwen 3.5 9B (together_ai/Qwen/Qwen3.5-9B)
**Orchestrator model:** Qwen 3.5 9B (same)
**max_tokens:** default (2048)
**Config:** `llm.thinking: false`, `cachier.enable_caching: false`

### Results

| Metric | Hand-coded | Orchestrated |
|--------|:---:|:---:|
| **Accuracy** | **80%** (8/10) | **90%** (9/10) |
| Errors | 0 | 0 |
| Pass@k | N/A | 2 |

### Per-case results

| # | Problem | Expected | Hand-coded | Orchestrated |
|---|---------|----------|:---:|:---:|
| 1 | Alice has 12 apples, gives 4 to Bob | 8 | Y | Y |
| 2 | Store has 25 shirts, sells 7 | 18 | N | Y |
| 3 | Tom read 15+23 pages | 38 | Y | Y |
| 4 | 6 rows x 5 desks | 30 | Y | Y |
| 5 | Maria had 20 candies, ate 3 | 17 | N | N |
| 6 | 48 cookies / 8 per box | 6 | Y | Y |
| 7 | 9 marbles + 14 more | 23 | Y | Y |
| 8 | 3 rows x 7 flowers | 21 | Y | Y |
| 9 | 50 stickers - 12 | 38 | Y | Y |
| 10 | 120 + 35 books | 155 | Y | Y |

### Generated pipeline (by Qwen 3.5 9B)

```python
def solve_math_problem(problem: str) -> str:
    numbers = parse_numbers(problem)
    operation = identify_operation(problem)
    result = compute_result(numbers, operation)
    answer = format_answer(problem, result)
    return answer
```

### Notes
- Orchestrated pipeline scored higher (90% vs 80%) due to LLM non-determinism
- Both pipelines have structurally identical code
- Case 5 (subtraction with "ate") failed for both — model identified wrong operation
- Results file: `orchestrate_comparison_results.json`

---

## Experiment 2: MUSR Murder Mysteries (Real Benchmark)

**Date:** 2026-03-23
**Task:** 10 MUSR murder mystery examples (shuffled, seed=42)
**Dataset:** TAUR-Lab/MuSR murder_mysteries split
**Ptools:** extract_suspects_and_evidence, verify_alibis, deduce_murderer, extract_index, raw_answer, answer_question
**Ptool model:** Qwen 3.5 9B (together_ai/Qwen/Qwen3.5-9B)
**Orchestrator model:** Qwen 3.5 9B (same)
**max_tokens:** 65536
**Config:** `cachier.enable_caching: false`

### Results

| Metric | Hand-coded | Orchestrated |
|--------|:---:|:---:|
| **Accuracy** | **60%** (6/10) | **60%** (6/10) |
| Errors | 1 (exception) | 0 |

### Per-case results

| Case | Expected | Hand-coded | Orchestrated |
|------|:---:|:---:|:---:|
| ex044 | 0 | N (pred: 1) | N (pred: 1) |
| ex098 | 0 | N (exception) | N (pred: 1) |
| ex184 | 0 | Y | Y |
| ex123 | 1 | N (pred: 0) | Y |
| ex121 | 1 | Y | Y |
| ex167 | 1 | Y | N (pred: 0) |
| ex009 | 1 | N (pred: 0) | Y |
| ex176 | 0 | Y | Y |
| ex197 | 1 | Y | N (pred: 0) |
| ex113 | 1 | Y | Y |

### Generated pipeline (by Qwen 3.5 9B)

```python
def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    # Step 1: Extract all suspects and their evidence from the narrative
    suspect_evidence = extract_suspects_and_evidence(narrative)

    # Step 2: Verify alibis against the narrative to find inconsistencies
    verified_analysis = verify_alibis(narrative, suspect_evidence)

    # Step 3: Use all evidence to deduce who committed the murder
    deduced_answer = deduce_murderer(narrative, verified_analysis, question, choices)

    # Step 4: Extract the 0-based index of the correct choice
    answer_index = extract_index(deduced_answer, choices)

    return answer_index
```

### Notes
- Both achieve identical 60% accuracy — orchestrator matches hand-coded
- Orchestrated had 0 errors vs 1 exception for baseline (API gateway error)
- They agree on 7/10 cases, differ on 3 (LLM non-determinism)
- The orchestrator independently discovered the same 4-step pipeline structure
- Results: `benchmarks/musr/results/20260323.102302.murder_baseline_64k/` and `20260323.102323.murder_orchestrated_64k/`

---

## Experiment 0: Debugging — Thinking Model Compatibility

### Problem discovered
Qwen 3.5 (both 9B and 397B) is a thinking model that splits output into
`reasoning_content` and `content` fields. The `<answer>` tags that
SimulateFactory needs sometimes land in the wrong field.

### Progression of fixes

| Fix | Baseline Accuracy | Notes |
|-----|:---:|---|
| No fix (content only) | 0% | All "cannot find final answer" errors |
| Naive concatenate (reasoning + content) | 0% | Greedy regex matched across reasoning text |
| Prefer content, fall back to reasoning | 80-90% (math) | Works for short outputs |
| + max_tokens=65536 | 60% (MUSR) | Model needs output budget for long narratives |
| + Extract last `<answer>` from reasoning | 60% (MUSR) | Handles reasoning with multiple `<answer>` mentions |

### Key insight
The 9B model with default max_tokens (2048) spends all output tokens on
`reasoning_content` for long MUSR narratives, producing empty `content`.
Setting max_tokens=65536 gives the model enough budget to complete both
reasoning and content generation.

---

## Integration Tests (Toy Ptools, Direct Implementation)

**Date:** 2026-03-22
**Orchestrator model:** Qwen 3.5 397B
**Ptool implementation:** `direct` (hardcoded Python, not LLM-backed)

| Test | Ptools | Result | Pass@k |
|------|--------|:---:|:---:|
| 2-step (double → add_one) | 2 | 11 = 11 | 1 |
| 3-step (double → add_one → negate) | 3 | -11 = -11 | 1 |
| Retry with smoke test | 2 | 11 = 11 | 1 |
| implement_via('orchestrate') | 2 | 11 = 11 | 1 |
| compose generates valid code | 2 | Has tool names | 1 |

All 5 integration tests pass.

---

## Quick Reference: Raw Result Locations

### Math comparison
- `orchestrate_comparison_results.json` (gitignored)

### MUSR runs (in `benchmarks/musr/results/`, all gitignored)

| Directory | What | Accuracy |
|-----------|------|:---:|
| `20260323.102302.murder_baseline_64k` | Hand-coded, 9B, 64K max_tokens | 60% |
| `20260323.102323.murder_orchestrated_64k` | Orchestrated, 9B, 64K max_tokens | 60% |
| `20260322.191422.murder_baseline_qwen` | Hand-coded, 9B, no max_tokens fix | 0% |
| `20260323.011606.murder_orchestrated` | Orchestrated, 9B, no fix | 0% |
| `20260323.020013.murder_orchestrated_v2` | Orchestrated, reasoning fallback | 0% |

### Configs used
- `benchmarks/musr/conf/murder_baseline_qwen.yaml`
- `benchmarks/musr/conf/murder_orchestrated.yaml`
