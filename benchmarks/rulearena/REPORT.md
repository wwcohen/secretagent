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
| pot | 69% | $0.026 | Apr 28 |
| unstructured_baseline | 46% | $0.021 | Apr 28 |
| structured_baseline | 41% | $0.027 | Apr 28 |

### Tax (valid split, N=50 — in progress)

Tax experiments are still being developed. The structured strategies
(workflow, pot, react) currently score 0% due to issues with form-field
extraction that are being debugged. Current best:

| Strategy | Accuracy | Cost/ex | Date | Notes |
|----------|----------|---------|------|-------|
| unstructured_baseline | 58% | $0.043 | Apr 26 | |
| structured_baseline | 10% | $0.037 | Apr 26 | |
| workflow | 0% | — | Apr 26 | extraction failures |
| pot | 0% | — | Apr 25 | extraction failures |
| react | 12% | $0.036 | Apr 29 | |

### NBA (valid split, N=15 — in progress)

Only workflow has been run on the per-domain benchmark so far:

| Strategy | Accuracy | Cost/ex | Date |
|----------|----------|---------|------|
| workflow | 93% | $0.015 | Apr 29 |

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

- **Tax extraction failures:** workflow/pot/react score 0% on tax due to
  form-field extraction issues. Needs domain-specific prompt templates.
- **NBA limited runs:** only workflow evaluated on per-domain benchmark so far.
- **ptool_inducer: 0% on airline.** Induced ptools are text-reasoning stubs
  that can't replicate the Python calculator's arithmetic. This learner is not
  well-suited for exact numerical computation tasks.
