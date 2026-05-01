# FinQA Benchmark Report

## Dataset

[FinQA](https://aclanthology.org/2021.emnlp-main.300) (Chen et al., EMNLP 2021): numerical reasoning over financial reports.
Each instance provides surrounding text, a markdown table from an SEC filing, and a question requiring arithmetic or percentage reasoning.

| Split | Source file | Cases | Labels |
|-------|-------------|-------|--------|
| train | `train.json` | ~6,251 | yes |
| valid (dev) | `dev.json` | ~883 | yes |
| test | `test.json` | ~1,147 | yes |

Gold answers are floats (`exe_ans`) representing exact numeric results.

## Experiment Conditions

All five experiments use the same model (`together_ai/deepseek-ai/DeepSeek-V3.1`) and the same evaluator (`FinQAEvaluator`).

| expt_name | Method | Description |
|-----------|--------|-------------|
| `workflow` | `direct` → `answer_finqa_workflow` | **Main result.** Hand-coded workflow using engineered ptools. LLM extracts reasoning plan (target + formula); Python evaluates the formula. Falls back to LLM extraction. |
| `pot` | `program_of_thought` | Ablation: drop the workflow, keep ptools. LLM writes Python with `parse_table` and `compute` as available tools. |
| `react` | `simulate_pydantic` | Ablation: drop the workflow, keep ptools. Pydantic-ai ReAct agent with `parse_table`, `lookup_cell`, `compute`, and `extract_reasoning_plan` as tools. |
| `structured_baseline` | `simulate` | Ablation: drop workflow and ptools. Single `simulate` call on `answer_finqa`. |
| `unstructured_baseline` | `prompt_llm` + coercion | Ablation: drop workflow, ptools, and structured prompt. Zero-shot prompt followed by answer extraction. |

## Results (valid split, N=300)

| expt_name | Accuracy | Cost/ex | Latency/ex | Exceptions |
|-----------|----------|---------|------------|------------|
| structured_baseline | 79.6%* | $0.0011 | 18.1s | 0 |
| workflow | 65.7% | $0.0012 | 4.9s | 0 |
| unstructured_baseline | 57.7% | $0.0007 | 2.4s | 0 |
| react | 49.0% | $0.0084 | 238.1s | 0 |
| pot | 44.3% | $0.0017 | 16.6s | 17 |

*\* structured_baseline: partial run (54/300 cases). Needs re-run.*

TODO:
run workflow with everything simulated
split ptools w direct imp into docstring and types and the function imp
workflow on training data

![Cost vs Accuracy](results_plot.png)

## Analysis

### Structured baseline vs workflow

The structured baseline uses a single `simulate` call — the LLM sees the `answer_finqa` function signature and docstring as a prompt. The workflow decomposes the task: `extract_reasoning_plan` (LLM) produces a plan with a formula, then `compute` (Python) evaluates it, falling back to `extract_final_number` (LLM) if no formula is found.

The structured baseline leads at 79.6% (on 54 cases — partial run, may shift with full 300). The workflow (65.7%) trails by ~14pp but demonstrates the ptool decomposition: separating *what to compute* (LLM judgment) from *doing the computation* (Python arithmetic). The high structured baseline suggests DeepSeek-V3.1 is strong at single-shot numerical reasoning on this task.

### Dropping the workflow hurts (pot and react)

When we drop the hand-coded workflow and let the LLM plan tool calls autonomously:

- **PoT** (44.3%): The model frequently generates prose instead of executable Python, causing 17 extraction exceptions. When code is generated, it often contains errors.
- **ReAct** (49.0%): The pydantic-ai agent loop is very expensive ($0.0084/ex) and slow. DeepSeek-V3.1 sometimes emits raw tool-call tokens instead of properly invoking tools, producing garbage output.

Both ablations underperform the structured baseline, suggesting the hand-coded workflow provides significant value for this task.

### Unstructured baseline

The unstructured baseline (57.7%) uses a zero-shot prompt with `<answer>` tags followed by a direct Python coercion step. It outperforms both pot and react, showing that for this task a well-crafted prompt without tools can beat autonomous tool-use strategies.

## Scoring

`FinQAEvaluator` in `evaluator.py`: numeric-tolerant matching with `rel_tol=2e-3`.
Handles `%` vs decimal gold (e.g. prediction `93.5%` matches gold `0.935`), `<answer>` tag stripping,
currency symbol removal (`$`, `€`, `£`), unit word stripping (`million`, `billion`),
and multi-line output normalization (prefers first numeric line).

## Ptool Design

### Python tools (direct)

- **`parse_table(problem)`**: Extracts the markdown table into clean tab-separated text.
- **`lookup_cell(problem, row_label, column)`**: Fuzzy row/column lookup returning exact cell values.
- **`compute(expression)`**: Safe arithmetic evaluation with `$`/`,` stripping.

### LLM ptools (simulate)

- **`extract_reasoning_plan(problem)`**: Produces a structured plan (target, values with row/col refs, formula with numbers substituted).
- **`extract_final_number(verbose_output)`**: Cleans verbose LLM output to a bare number.

### Design principle

The LLM handles *understanding and planning* while Python handles *data retrieval and arithmetic*. This avoids LLM-to-LLM passthroughs that add cost and error propagation.

## Reproducing

All experiments use the generic CLI (`secretagent.cli.expt`) from `benchmarks/finqa/`:

```bash
cd benchmarks/finqa

# Run all five (or individually: make workflow, make pot, etc.)
make basics

# Analyze results
make avg
make plot

# Export to benchmarks/COMMON/results/finqa/finqa/
make export
```
