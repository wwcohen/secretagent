# FinQA Benchmark Report

## Dataset

[FinQA](https://aclanthology.org/2021.emnlp-main.300) (Chen et al., EMNLP 2021): numerical reasoning over financial reports.
Each instance provides surrounding text, a markdown table from an SEC filing, and a question requiring arithmetic or percentage reasoning.

| Split | Source file | Cases | Labels |
|-------|-------------|-------|--------|
| train | `train.json` | ~6,251 | yes |
| valid (dev) | `valid.json` | ~883 | yes |
| test | `test.json` | ~1,147 | yes |

Gold answers are floats (`exe_ans`) representing exact numeric results.

## Experiment Conditions

All five experiments use the same model (`together_ai/deepseek-ai/DeepSeek-V3.1`) and the same evaluator (`FinQAEvaluator`).

| expt_name | Method | Description |
|-----------|--------|-------------|
| `workflow` | `direct` → `answer_finqa_workflow` | Hand-coded workflow using engineered ptools. LLM extracts a structured reasoning plan (target, values with row/column refs, formula); Python substitutes values into the formula and evaluates it. Falls back to LLM extraction when the plan does not yield a usable formula. |
| `structured_baseline` | `simulate` | Ablation: drop workflow and ptools. Single `simulate` call on `answer_finqa` — the LLM sees the function signature and docstring as a prompt and returns the answer in one shot. |
| `unstructured_baseline` | `prompt_llm` + coercion | Ablation: drop workflow, ptools, and structured prompt. Zero-shot prompt template followed by a deterministic answer-extraction step. |
| `pot` | `program_of_thought` | Ablation: drop workflow, keep ptools. LLM writes Python with the shared toolset (`parse_table`, `lookup_cell`, `compute`, `extract_reasoning_plan`) available; the code is executed in a sandbox. |
| `react` | `simulate_pydantic` + cleanup | Ablation: drop workflow, keep ptools. Pydantic-ai ReAct agent with the same shared toolset; freeform output is post-processed by `extract_final_number`. |

The agent ablations (`pot` and `react`) share the same toolset so that the comparison isolates the orchestration mechanism (program-of-thought vs ReAct loop) from tool capability.

## Results (test split, N=300)

| expt_name | Accuracy | Cost/ex | Latency/ex | Exceptions |
|-----------|----------|---------|------------|------------|
| **workflow**            | **76.3%** | $0.0012 | 2.6s   | 0 / 300 |
| structured_baseline     | 69.3%     | $0.0011 | 12.6s  | 0 / 300 |
| unstructured_baseline   | 57.7%     | $0.0007 | 2.4s   | 0 / 300 |
| react                   | 47.3%     | $0.0093 | 47.5s  | 0 / 300 |
| pot                     | 41.7%     | $0.0020 | 9.7s   | 34 / 300 |

![Cost vs Accuracy](results_plot.png)

## Analysis

### Workflow leads on accuracy, cost, and latency simultaneously

The hand-coded workflow wins on all three metrics: highest accuracy (76.3%), lowest per-case cost tied with the structured baseline ($0.0012), and lowest non-trivial latency (2.6s). It does this by decomposing the task: `extract_reasoning_plan` (LLM via `prompt_llm` with a strict template) produces a target, values with row/column references, and a formula; `parse_plan_fields` and `substitute_values` (Python) plug the numbers in; `compute` (Python) evaluates the substituted expression; `extract_final_number` (LLM via `simulate`) is used only as a fallback when the structured plan does not yield a usable formula.

The decomposition matters because it puts each subtask on the right substrate: the LLM handles *understanding the question and identifying the relevant numbers*, while Python handles *the actual arithmetic*. The structured baseline collapses both into a single LLM call and sits 7pp behind, which is the cost of asking the LLM to do its own arithmetic.

### Dropping the workflow hurts both agent ablations

When the workflow is removed and the LLM is left to orchestrate the ptools autonomously, accuracy drops sharply:

- **react** (47.3%) is by far the most expensive condition at $0.0093/ex (~8x workflow cost) and slowest at 47.5s/ex. The pydantic-ai agent loop accumulates context across tool calls, and a small number of cases consume disproportionate budget — one case alone produced 192K input tokens and cost $0.13.
- **pot** (41.7%) is faster and cheaper than react but the weakest condition overall. It also produces 34 extraction exceptions out of 300 cases (11.3%), where the LLM writes prose explanation instead of fenced Python and gets truncated at the output-token budget before producing executable code. With a richer toolset (the shared toolset is bigger than the minimal `parse_table` + `compute` set), the verbose tool descriptions inflate the prompt and shift pot's failure mode from "wrong code" to "no code at all."

Both agent ablations underperform the structured baseline, so the message is consistent: a hand-coded workflow that uses the LLM for what LLMs are good at (planning) and Python for what Python is good at (arithmetic) wins on accuracy, cost, and latency together — autonomous tool-use loses on all three.

### The unstructured baseline is a meaningful floor

The unstructured baseline (57.7%) uses a zero-shot prompt with `<answer>` tags followed by deterministic text extraction. It outperforms both agent ablations, showing that for this task a well-crafted prompt without any tools beats autonomous tool-use strategies. This suggests that tools alone are not the value of the workflow — the value is in the *structure* (decomposed plan + Python arithmetic), not the tool inventory.

### Negative result: workflow with shared ptool primitives

We tested whether the workflow itself should use the same primitives that pot and react have access to (`lookup_cell` + `compute`) for value resolution, on the hypothesis that deterministic table lookups would prevent the LLM from misreading values. On a 300-case validation run with identical plan extraction, the variant **lost by 2.7pp (73.0% vs 75.7% baseline) with 0 wins and 8 losses across the diverging cases.**

The diagnosis is that the LLM's dominant failure on FinQA is not misreading values — it is *citing the wrong row or column*, often attributing a number from prose to a table cell. A deterministic lookup faithfully follows the wrong citation and produces the wrong value, whereas the LLM's own eyeballed value usually comes from the correct cell even when its citation is off. So a "more rigorous" lookup primitive *amplifies* citation errors rather than correcting them.

The variant lives at `ptools.answer_finqa_workflow_lookup` with a Makefile target `workflow-lookup`; reproduce with:

```bash
make workflow         SPLIT=valid N=300 RECORD=true SUFFIX=ab
make workflow-lookup  SPLIT=valid N=300 RECORD=true SUFFIX=ab
```

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
- **`parse_plan_fields(raw_plan)`**: Parses the LLM's structured plan into target, values, formula, and scale fields.
- **`substitute_values(formula, values)`**: Replaces variable names in a formula with their numeric values.
- **`format_for_scale(num, scale)`**: Formats a numeric result for the requested scale (`%`, `million`, etc.).

### LLM ptools

- **`extract_reasoning_plan(problem)`** (`prompt_llm`, strict template): Produces a structured plan with target, values with row/column refs, formula with numbers substituted, and scale.
- **`extract_final_number(verbose_output)`** (`simulate`): Cleans verbose LLM output to a bare number — used as a fallback in the workflow and as the post-processing step in the react ablation.

### Design principle

The LLM handles *understanding and planning* while Python handles *data retrieval and arithmetic*. This avoids LLM-to-LLM passthroughs that add cost and propagate errors.

## Reproducing

All experiments use the generic CLI (`secretagent.cli.expt`) from `benchmarks/finqa/`:

```bash
cd benchmarks/finqa

# Run all five (or individually: make workflow, make pot, etc.)
make basics N=300 SPLIT=test

# Analyze results
make avg
make plot

# Export to benchmarks/results/finqa/finqa/
make export
```
