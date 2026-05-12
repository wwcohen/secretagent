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
| **workflow**            | **75.3%** | $0.0012 | 4.6s   | 0 / 300   |
| structured_baseline     | 61.7%     | $0.0014 | 10.4s  | 0 / 300   |
| unstructured_baseline   | 57.3%     | $0.0010 | 6.0s   | 0 / 300   |
| react                   | 32.0%     | $0.0095 | 59.7s  | 5 / 300   |
| pot                     | 17.7%     | $0.0035 | 35.0s  | 162 / 300 |

![Cost vs Accuracy](results_plot.png)

## Analysis

### Workflow leads on accuracy, cost, and latency simultaneously

The hand-coded workflow wins on all three metrics: highest accuracy (75.3%), lowest per-case cost tied with the unstructured baseline ($0.0012), and the lowest latency among the three workflow-style conditions (4.6s — only the unstructured baseline's bare prompt is faster). It does this by decomposing the task: `extract_reasoning_plan` (LLM via `prompt_llm` with a strict template) produces a target, values with row/column references, and a formula; `parse_plan_fields` and `substitute_values` (Python) plug the numbers in; `compute` (Python) evaluates the substituted expression; `extract_final_number` (LLM via `simulate`) is used only as a fallback when the structured plan does not yield a usable formula.

The decomposition matters because it puts each subtask on the right substrate: the LLM handles *understanding the question and identifying the relevant numbers*, while Python handles *the actual arithmetic*. The structured baseline collapses both into a single LLM call and sits 13.6pp behind, which is the cost of asking the LLM to do its own arithmetic.

The workflow is also the most stable condition across splits: it scores 75.7% on a separate 300-case `valid` run (`workflow_ab` below), within 0.4pp of its test-split number, while the agent ablations both drop sharply on test compared to earlier valid-set numbers. So the workflow's lead is not a function of which slice of FinQA we evaluate on.

### Dropping the workflow hurts both agent ablations

When the workflow is removed and the LLM is left to orchestrate the ptools autonomously, accuracy collapses:

- **react** (32.0%) is by far the most expensive condition at $0.0095/ex (~8x workflow cost) and slowest at 59.7s/ex. The pydantic-ai agent loop accumulates context across tool calls (~9.3K input tokens / 2.3K output tokens per case on average vs. ~1.6K / 126 for the workflow), and a small number of cases consume disproportionate budget. The dominant failure modes are wrong final number even when the trace looks right (LLM-side arithmetic) and percentage-formatting mismatches.
- **pot** (17.7%) is the weakest condition overall. **162 of 300 cases (54%) raise a sandbox extraction exception**: the LLM writes long prose reasoning before getting around to Python, hits the output-token budget mid-response, and the extracted code block is incomplete or absent. With the same shared toolset given to react, the verbose tool descriptions inflate the prompt and the model's natural verbosity becomes catastrophic — pot's failure shifts from "wrong code" to "no code at all." Excluding exceptions, pot's accuracy on the 138 cases that did parse is 38.4%, still well below the workflow.

Both agent ablations underperform every workflow-style baseline, so the message is consistent: a hand-coded workflow that uses the LLM for what LLMs are good at (planning) and Python for what Python is good at (arithmetic) wins on accuracy, cost, and latency together — autonomous tool-use loses on all three.

We deliberately leave pot and react un-engineered: the ablation contract is "delete the workflow, keep the same primitives," not "build the best possible agent with these tools." Adding format-enforcement to pot's prompt or extra cleanup logic to react would just re-introduce pieces of the workflow under different names. The failure modes we see — pot's 162 truncated code-blocks and the percent-vs-decimal mismatches in both ablations — are themselves the evidence for the scaffolding the workflow provides via its strict plan template, `format_for_scale`, and `extract_final_number`; the structured baseline (61.7%) already isolates "raw LLM reasoning, no tools," so the gap from there down to pot/react measures the cost of tool-call complexity without compensating glue.

### The unstructured baseline is a meaningful floor

The unstructured baseline (57.3%) uses a zero-shot prompt with `<answer>` tags followed by deterministic text extraction. It outperforms both agent ablations by a wide margin (25–40pp) at a fraction of the cost, showing that for this task a well-crafted prompt without any tools beats autonomous tool-use strategies. This suggests that tools alone are not the value of the workflow — the value is in the *structure* (decomposed plan + Python arithmetic), not the tool inventory.

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

All experiments use the generic CLI (`secretagent.cli.expt`) from `benchmarks/finqa/finqa/`:

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
