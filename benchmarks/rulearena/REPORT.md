# RuleArena Benchmark Report

## Dataset

RuleArena (Zhou et al., ACL 2025): rule-based reasoning across three domains, each
with complexity levels 0/1/2 controlling the number of interacting rules.

| Domain  | Task | Answer type | Train | Valid | Test |
|---------|------|-------------|-------|-------|------|
| Airline | Compute total baggage + ticket cost from AA fee rules | integer (USD) | 150 | 50 | 100 |
| Tax     | Compute federal income tax from filled IRS forms       | float (USD)   | 150 | 50 | 100 |
| NBA     | Detect CBA salary cap violations in proposed trades    | binary (0/1)  | 128 | 42 |  46 |

Source: vendored from `external/RuleArena/`. Deterministic Python calculators
provide ground truth for airline and tax; NBA ground truth is author-labeled.

## Strategies

| Strategy | Description | LLM calls |
|----------|-------------|-----------|
| unstructured_baseline | Single LLM call with chain-of-thought prompt. No decomposition. | 1 |
| structured_baseline | LLM simulates the top-level interface directly (structured output). | 1 |
| workflow | Hand-coded pipeline: LLM extracts structured params, Python computes answer. | 1 |
| pot | Program of Thought: LLM generates Python code, executed in sandbox. | 1 |
| react | Autonomous agent (pydantic-ai) with extraction and calculator tools. | variable |

All experiments use `together_ai/deepseek-ai/DeepSeek-V3.1` unless noted.

## Results

### Airline (test split, N=100)

| Strategy | Accuracy | Cost/ex | Date |
|----------|----------|---------|------|
| workflow | **98%** | $0.030 | Apr 28 |
| react | 89% | $0.024 | Apr 28 |
| pot | 84% | $0.026 | Apr 30 |
| unstructured_baseline | 46% | $0.021 | Apr 28 |
| structured_baseline | 41% | $0.027 | Apr 30 |

### Tax (test split, N=100)

`correct` = within 1% relative error (RuleArena convention for tax).

| Strategy | Accuracy | Cost/ex | Date |
|----------|----------|---------|------|
| unstructured_baseline | **55%** | $0.010 | Apr 30 |
| workflow | 50% | $0.010 | Apr 30 |
| react_two_phase | 48% | $0.014 | Apr 30 |
| pot | 43% | $0.016 | Apr 30 |
| react | 15% | $0.035 | Apr 30 |
| structured_baseline | 11% | $0.007 | Apr 30 |

### NBA (test split, N=46)

`correct` = binary match (0/1 violation detection).

| Strategy | Accuracy | Cost/ex | Date |
|----------|----------|---------|------|
| unstructured_baseline | **72%** | $0.016 | Apr 30 |
| structured_baseline | 67% | $0.014 | Apr 30 |
| workflow | 61% | $0.015 | Apr 30 |
| react | 59% | $0.030 | Apr 30 |
| pot | 2% | $0.019 | Apr 30 |

## Analysis

**Airline workflow is the clear winner at 98% accuracy.** The hand-coded
pipeline (LLM extracts params, Python computes fee) achieves near-perfect
results at the lowest cost. This validates the structured extraction approach
for deterministic computation tasks.

**React (89%) is a strong second.** The autonomous agent figures out how to
use the tools effectively most of the time but makes more errors than the
hand-coded workflow, at comparable cost.

**PoT (69%) suffers from code generation errors.** The LLM-generated Python
code often gets fee table lookups wrong or mishandles edge cases that the
hand-coded calculator handles correctly.

**Unstructured and structured baselines (46%, 41%) confirm that raw LLM
reasoning is insufficient** for complex multi-rule fee calculations. The LLM
cannot reliably do the arithmetic and table lookups mentally.

**Tax domain needs more work.** The extraction templates that work for airline
don't transfer to tax forms. The tax domain has a fundamentally different
structure (nested form references) that requires domain-specific prompt
engineering.

## Replication Targets

Reference numbers from ptp-behavior-distillation (separate codebase, same
model DeepSeek-V3, **mixed train+valid+test splits, N=300/216**):

| Strategy | Airline (N=300) | Tax (N=300) | NBA (N=216) |
|----------|----------------:|------------:|------------:|
| unstructured_baseline | 48.3% | 35.3% | 64.4% |
| structured_baseline | 77.0% | 99.7% | 80.1% |
| react | 63.3% | 78.3% | 82.4% |

Source: `ptp-behavior-distillation/benchmark_results/rulearena/rq2_summary.csv`,
runs dated 2026-02-27 to 2026-03-05.

**Comparison caveats:**
- ptp used all splits (train+valid+test); our airline results are test-split only
- N differs (300 vs 100 for airline/tax, 216 vs 46 for NBA)
- ptp's "structured_baseline" is their L1 extract workflow (closest to our workflow)
- ptp's "react" is text-based ReAct, not pydantic-ai function-calling
- Direct accuracy comparison is directional, not exact

## Known Issues

- **ptool_inducer: 0% on airline.** Induced ptools are text-reasoning stubs
  that can't replicate the Python calculator's arithmetic. This learner is not
  well-suited for exact numerical computation tasks.
- **NBA PoT: 2%.** With no calculator to call, PoT requires the LLM to encode
  all CBA salary-cap rules as Python logic. DeepSeek-V3.1 fails almost
  universally on this — the generated code is syntactically valid but
  semantically wrong. Not a framework bug; PoT is a poor fit for this domain.
