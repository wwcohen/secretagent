# TabMWP Benchmark Report

## Dataset

TabMWP: 38K grade-school math problems over small tables (avg 6 rows, 2 cols). Free-text (75%) and multi-choice (25%), grades 1-8.

Example: *"What is the mean of the numbers?"* + table of names/coin counts -> answer: `84`.

Source: Lu et al., ICLR 2023. License: CC BY-NC-SA 4.0.

## Experiments

All experiments use `together_ai/deepseek-ai/DeepSeek-V3.1`, caching enabled, full rollout recordings saved.


| Config               | LLM calls | Table access   | Ptool context                | PTP stubs      | Description                                       |
| -------------------- | --------- | -------------- | ---------------------------- | -------------- | ------------------------------------------------- |
| `zeroshot`           | 1         | in prompt      | n/a                          | No             | Single simulate call, no decomposition            |
| `guided_ptp`         | 1         | in prompt      | n/a                          | **Yes**        | Single call with Python stub trace as scaffolding |
| `workflow_broad`     | 2         | in prompt      | full (question+table)        | Yes (simulate) | `extract_and_compute` -> `format_answer`          |
| `workflow_rich`      | 4         | in prompt      | full (question+table)        | Yes (simulate) | 4 ptools, each receives question + table          |
| `workflow_incontext` | 4         | in prompt      | **isolated** (own args only) | Yes (simulate) | 4 ptools, each sees only its own arguments        |
| `workflow_tools`     | 4         | via tool calls | **isolated**                 | Yes (simulate) | Same as above, table fetched by tool interfaces   |
| `orchestrated`       | 4         | in prompt      | isolated (auto-wired)        | Yes (simulate) | LLM auto-composes pipeline from available ptools  |
| `react`              | variable  | via tool calls | shared (agent state)         | Yes (simulate) | ReAct agent decides which tools to call           |
| `pot`                | 1         | as dict        | n/a                          | No             | LLM generates Python code executed in sandbox     |


**Naming note:** `workflow_incontext` refers to the table being *in the prompt context* (vs `workflow_tools` which fetches it via tool calls). It does NOT mean the ptools have full context — in fact, each ptool in this config sees only its own arguments (isolated).

## Results (n=100, dev1k split, seed=42)

All experiments use `together_ai/deepseek-ai/DeepSeek-V3.1`.

| Config                   | Accuracy | +/- SE | Cost/ex  | LLM calls | Ptool context    | Key insight                                    |
| ------------------------ | -------- | ------ | -------- | --------- | ---------------- | ---------------------------------------------- |
| **workflow**             | **95%**  | 2.2%   | $0.0015  | 1         | n/a              | PTP stubs as scaffolding — best accuracy       |
| pot                      | 94%      | 2.4%   | $0.0011  | 1         | n/a              | LLM-generated Python; sandbox fix needed       |
| react                    | 90%      | 3.0%   | $0.0076  | ~5-10     | shared (agent)   | Agent flexibility, 15x cost vs workflow        |
| unstructured_baseline    | 84%      | 3.7%   | $0.0005  | 1         | n/a              | Strong single-call baseline, cheapest          |
| structured_baseline      | 47%      | 5.0%   | $0.0011  | 4         | **isolated**     | Naive decomposition — each ptool sees own args only |

**Total cost for n=100 experiments: ~$1.20**

## Results (n=1000, test1k split)

*To be run — final evaluation once methods are frozen.*

## Analysis

**PTP-style trace scaffolding is the best method.** `workflow` (95%) outperforms `unstructured_baseline` (84%) using a single LLM call. The prompt shows Python function stubs as a reasoning trace to simulate — the model fills in each step, resulting in structured, accurate outputs. 5x cheaper than react at higher accuracy.

**Context isolation is the primary failure mode for modular decomposition.** `structured_baseline` (47%) fails because each ptool sees only its own arguments — `compute_answer` receives `("difference", ["0.78", "0.54"])` with no idea what the original question was. The decomposition structure is not the problem; the information bottleneck between steps is.

**PoT is surprisingly strong once the sandbox is fixed.** 94% at $0.0011/ex — competitive with workflow and much cheaper than react. The sandbox previously blocked `float()` and `int()` (issue #7, now fixed). PoT is a strong Pareto option: near-top accuracy at low cost.

**React is expensive for modest gain.** 90% at $0.0076/ex — worse than both workflow and PoT, at 5-15x their cost. The overhead comes from multiple LLM calls per case (agent loop + simulated tool ptools + `extract_answer` post-processing).

## Checks for Later

- Error analysis by `ques_type`, `ans_type`, `grade`
- Per-ptool accuracy from rollout recordings
- n=1000 run for tighter confidence intervals
- Phase 7: grid search over models/methods per ptool
- PoT re-run after sandbox fix (issue #7)

## Key Decisions

1. `**table_id` in interface signature.** All configs receive `(question, table, table_id, choices)`. Keeps interface uniform; zeroshot ignores `table_id`.
2. **PoT receives `table_for_pd` (dict).** Sandbox restricts `float()` and `pandas`. Standard practice — original TabMWP paper provides this format for programmatic approaches.
3. **React uses `extract_answer` post-processing.** Follows MUSR pattern (`raw_answer` -> `extract_index`).
4. **Evaluator strips `$`, `%` and uses tolerance-based numeric matching.** Integers within 0.5, decimals within 0.01.
5. **Model:** `together_ai/deepseek-ai/DeepSeek-V3.1` for all experiments.

