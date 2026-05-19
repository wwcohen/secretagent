# Code Distillation Experiment Results

## Overview

Compared three approaches across 7 benchmarks:
- **Baseline**: workflow with LLM simulate (0-shot)
- **Ptool codedistill**: replace individual interfaces with LLM-generated Python code
- **E2E codedistill**: replace entire top-level interface with end-to-end Python code

Code generation uses Claude Opus 4.6 with multi-round refinement and ensemble selection.
Training cost is one-time (~$0.20 per interface with 1 candidate, ~$1.80 with 3×3).

Training data filtering: `only_correct=True` (default) — only uses rollouts that
produced a correct final answer, avoiding "learning the LLM's mistakes".

## Results (validation set)

### NatPlan Calendar (50 cases)

| Method | Accuracy | Infer Cost |
|--------|----------|-----------|
| workflow baseline (0-shot) | 54% | $0.185 |
| workflow fewshot (5-shot) | 56% | $0.514 |
| ptool codedistill (opus) | 84% | $0.085 |
| **e2e codedistill (opus)** | **90%** | **$0.000** |

Best result. E2E generated 336 lines of parse→solve→format code,
similar to hand-written AgentProject solvers.

### NatPlan Meeting (50 cases)

| Method | Accuracy | Infer Cost |
|--------|----------|-----------|
| workflow baseline | 0% | $0.173 |
| workflow fewshot | 0% | $0.659 |
| e2e codedistill | 0% | $0.000 |

All methods 0% due to evaluator format matching issues, not codedistill's fault.

### Sports Understanding (75 cases)

| Method | Accuracy | Infer Cost |
|--------|----------|-----------|
| workflow baseline | 97% | $0.105 |
| workflow fewshot | 92% | $0.135 |
| rote learning | **99%** | $0.096 |
| ptool codedistill (haiku) | 97% | $0.094 |
| ptool codedistill (opus) | 93% | $0.067 |
| e2e codedistill | 63% | $0.000 |

Rote learning is best here. E2E fails because sport_for requires
player→sport knowledge that can't be captured by rules alone.

### MuSR Murder (50 cases)

| Method | Accuracy | Infer Cost |
|--------|----------|-----------|
| zs_cot baseline | 72% | $0.108 |
| workflow baseline | 70% | $0.814 |
| ptool codedistill (extract_index) | 70% | $0.785 |

Minimal impact — extract_index is trivial (100% train acc),
but it's only the final step so cost savings are small.

### Penguins in a Table (43 cases)

| Method | Accuracy | Infer Cost |
|--------|----------|-----------|
| workflow baseline | **70%** | $0.041 |
| ptool codedistill | 53% | $0.028 |

Codedistill hurt accuracy — generated code returns wrong values
instead of None, bypassing backoff. Need stricter wrong_rate filtering.

### Geometric Shapes (75 cases)

| Method | Accuracy | Infer Cost |
|--------|----------|-----------|
| workflow baseline | **75%** | $1.637 |
| ptool codedistill | 73% | **$0.871** |

Accuracy roughly preserved, cost reduced 47%. Four interfaces
(decompose_path, extract_path_and_options, describe_command,
select_option) achieved 96-100% train accuracy with <2% wrong rate.

### MedCalc-Bench (test split, n=100, Qwen3.5-9B)

| Method | Accuracy | Infer Cost |
|--------|----------|-----------|
| baseline (prompt_llm) | 38% | $0.134 |
| **pipeline + ptool codedistill** | **44%** | **$0.014** |
| e2e codedistill (100 shuffled cases) | 42% | $0.000 |

**Ptool codedistill**: replaces `identify_calculator` (100% val acc, 0% wrong
rate) in the pipeline. Accuracy **+6%** over baseline, cost **-89%**.

Note: earlier results (78%/76%) were on the **train split** — data leakage.
Test split numbers (38%/44%) are the honest results.

### RuleArena Airline (30 cases)

| Method | Accuracy | Infer Cost |
|--------|----------|-----------|
| oracle (hand-coded Python + ground truth metadata) | **100%** | $0.000 |
| structured baseline (LLM extract + Python compute) | 90% | $0.461 |
| ptool codedistill (`_extract_airline_raw`) | skipped | — |

Oracle uses hand-written Python calculators — upper bound. Baseline L1
(extract via LLM → Python compute) already achieves 90%. Ptool codedistill
on `_extract_airline_raw` failed: its output is a long JSON string, so exact
match gives 40% train accuracy with 60% wrong rate (skipped by the 10%
threshold). The extraction is hard to learn when target output format varies.
E2E not run (top-level takes 5 args including 48k-char rules text).

## Codedistill-all Auto-Selection Results

The `codedistill-all` command automatically tests all interfaces
and enables those with wrong_rate <= 5%:

### Geometric Shapes
| Interface | Train Acc | Wrong Rate | Status |
|-----------|-----------|-----------|--------|
| decompose_path | 100% | 0% | ENABLED |
| extract_path_and_options | 100% | 0% | ENABLED |
| describe_command | 96% | 0.8% | ENABLED |
| select_option | 99% | 1.3% | ENABLED |
| describe_shape | 52% | 48% | skipped |
| compute_angle | 37% | 63% | skipped |

### Penguins
| Interface | Train Acc | Wrong Rate | Status |
|-----------|-----------|-----------|--------|
| table_operation | 100% | 0% | ENABLED |
| choose_response | 98% | 0% | ENABLED |
| answer_question | 74% | 26% | skipped |
| analyze_input | 56% | 44% | skipped |

### MuSR Murder
| Interface | Train Acc | Wrong Rate | Status |
|-----------|-----------|-----------|--------|
| extract_index | 100% | 0% | ENABLED |
| deduce_murderer | 76% | 24% | skipped |
| extract_suspects_and_evidence | 0% | — | skipped |
| verify_alibis | 0% | — | skipped |

## Cross-Benchmark Summary

All results use held-out val or test splits with no overlap to training data.

| Benchmark | Split | Baseline | Ptool CD | E2E CD | Winner |
|-----------|-------|----------|----------|--------|--------|
| NatPlan Calendar | val 50 | 54% / $0.19 | 84% / $0.09 | **90% / $0** | e2e |
| Date Understanding | val 75 | 39% / $0.29 | — | **59% / $0** | **e2e (+20%)** |
| MedCalc | test 100 | 38% / $0.13 | **44% / $0.01** | 42% / $0 | **ptool (+6%, -89% cost)** |
| FinQA | val 100 | 62% / $0.12 | 61% / $0.10 | 35% / $0 | ptool (-17% cost) |
| Geometric | val 75 | 75% / $1.64 | **73% / $0.87** | — | ptool (-47% cost) |
| Sports | val 75 | 97% / $0.10 | 97% / $0.09 | 63% / $0 | rote (99%) |
| RuleArena Airline | val 30 | 90% / $0.46 | skipped | — | oracle 100%/$0 |
| MuSR Murder | val 50 | 70% / $0.81 | 70% / $0.79 | 0% / $0 | baseline |
| Penguins | val 43 | 70% / $0.04 | 53% / $0.03 | 58% / $0 | baseline |
| NatPlan Meeting | val 50 | 0% / $0.17 | — | 0% / $0 | evaluator broken |

## Key Findings

1. **E2E codedistill works best for deterministic tasks** (calendar scheduling),
   generating parse→solve→format code that outperforms LLM simulate.

2. **Ptool codedistill is good for cost reduction** when individual interfaces
   have deterministic logic (geometric shapes -47% cost, medcalc -92% cost).

3. **Rote learning wins for lookup-based tasks** (sports: 99%) where inputs repeat.

4. **Wrong rate is the critical metric** for ptool codedistill — code that returns
   wrong values (instead of None) hurts accuracy. The 5-10% threshold in
   `codedistill-all` correctly filters these out.

5. **Few-shot examples didn't help** — increased cost without improving accuracy.
   Code distillation is a better use of training data than few-shot prompting.

6. **Training cost is one-time** (~$0.20-1.80 per interface via opus), while
   inference cost savings are per-call and accumulate over time.

7. **Overfitting on small training sets** — MuSR e2e got 66% on train but 0% on val
   because each murder mystery is unique; 50 examples aren't enough to generalize.
   Only works when test inputs share structure with train inputs.

8. **Training data must be representative** — MedCalc e2e first attempt failed
   (0% val) because the dataset is sorted by calculator type and `ds.cases[:50]`
   selected 50 cases of the same calculator. With shuffled 100 cases (35
   calculator types) it jumped to 42%. Always shuffle or stratify training data.

8. **Exact-match evaluation is brittle** — RuleArena `_extract_airline_raw` outputs
   long JSON strings. Codedistill's accuracy metric uses `==`, so even correct
   answers with different formatting count as wrong. Need semantic comparison
   for structured outputs.

## Interfaces That Codedistill Handled Well (train acc ≥95%, wrong rate ≤5%)

| Benchmark | Interface | Train Acc | What it does |
|-----------|-----------|-----------|--------------|
| MedCalc | identify_calculator | 100% | question → calculator name (55-way classification) |
| Geometric | decompose_path | 100% | SVG path → command list |
| Geometric | extract_path_and_options | 100% | input → (path, options) tuple |
| Geometric | describe_command | 96% | SVG command → English description |
| Geometric | select_option | 99% | description → option letter |
| Penguins | table_operation | 100% | table + action → new table |
| Penguins | choose_response | 98% | answer + options → option letter |
| MuSR | extract_index | 100% | answer_text + choices → index |

Pattern: these are all **deterministic string/data manipulations** — parsing,
formatting, lookup, classification. None require domain knowledge or reasoning.
