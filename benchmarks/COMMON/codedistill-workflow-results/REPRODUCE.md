# How to reproduce the Class 2 (workflow distill) results

## Models

| role | opus | gemini |
|---|---|---|
| Learner (writes workflow Python) | `claude-opus-4-6` | `gemini/gemini-3.1-pro-preview` |
| Baseline simulate ptool | `together_ai/deepseek-ai/DeepSeek-V3.1` (V3 for musr/rulearena) | unchanged |
| Backoff path | falls back to baseline LLM via `backoff=true --backoff-method simulate` | same |

## Step 0: prerequisites

```bash
cd secretagent
set -a; source .env; set +a            # exposes API keys (GEMINI_API_KEY etc.)
uv sync
```

## Step 1: train recording (one-time per benchmark)

Same as Class 1 — see ../codedistill-ptools-results/REPRODUCE.md.

## Step 2: distill the workflow (Opus example)

```bash
cd benchmarks/<bench>
uv run -m secretagent.cli.learn workflow-codedistill \
  --interface <top_iface> \
  --dataset-file data/<bench>_train.json --output-field <gold_field> \
  --tool-module <ptools_module> --conf-file conf/<bench>.yaml \
  --reference-file ../<sibling_bench>/ptools.py \
  --trace-dir recordings_full/<latest>.<bench>_train_full \
  --learned-dir learned_class2_opus --model claude-opus-4-6 \
  --backoff true --backoff-method simulate
```

For Gemini variant, `--model gemini/gemini-3.1-pro-preview --learned-dir learned_class2_gemini`.

After distill, move outputs to COMMON:

```bash
git mv learned_class2_opus ../COMMON/codedistill-workflow-results/<bench>/
```

## Step 2.5: meeting golden_plan list→str hack

natplan_meeting's `expected_output['golden_plan']` is a **list** of step
strings, while `meeting_planning(prompt) -> str` interface expects a
single str. Without conversion, distill teaches the LLM to return a list,
which fails the SOLUTION-format evaluator.

Fix (apply once before distilling meeting):

```bash
uv run python -c "
import json
src = json.load(open('benchmarks/natural_plan/data/meeting_train.json'))
cases = src['cases'] if 'cases' in src else src
for c in cases:
    eo = c.get('expected_output')
    if isinstance(eo, dict) and isinstance(eo.get('golden_plan'), list):
        eo['golden_plan'] = 'SOLUTION:\n' + '\n'.join(eo['golden_plan'])
json.dump(src if 'cases' in src else cases, open('/tmp/meeting_train_v4g.json', 'w'), indent=2)
"
# Then point --dataset-file at /tmp/meeting_train_v4g.json
```

This bumped meeting class2 opus from 3% → 98%.

## Step 3: end-to-end val (Class 2)

```bash
uv run python expt.py run --config-file conf/<bench>.yaml \
  dataset.partition=valid dataset.n=100 \
  evaluate.expt_name=<bench>_val_full_class2_opus \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  llm.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
  ptools.<top_iface>.method=learned_code \
  ptools.<top_iface>.learner=workflow_distill \
  ptools.<top_iface>.backoff=true \
  learn.train_dir=$ROOT/benchmarks/COMMON/codedistill-workflow-results/<bench>/learned_class2_opus
```

## Step 4: test split eval

Same as Step 3 with `dataset.partition=test` (or `dataset.split=test` for
musr/bbh/medcalc/tabmwp). The cached learned.py is reused; only inference
runs. With `backoff=true`, ptools that return None fall back to baseline DS.

## Full orchestration scripts

- `benchmarks/jerry/class2_iters/run_class2_v4_full_workflow.sh` (opus Opus)
- `benchmarks/jerry/class2_iters/run_class2_v4g_gemini.sh` (gemini Gemini)
- `benchmarks/jerry/class2_iters/run_v4g_vals_watcher.sh` (poll-based val auto-launch)
- `benchmarks/jerry/class2_iters/run_test_split_vals_all.sh` (test-split eval orchestrator)

## Class 3 quirks

`benchmarks/jerry/class3_iters/run_class3_v4_full.sh` runs the 4-stage induced
pipeline. Notes:

- musr Class 3 needs `--state-module ptools_common --state-expr '_REACT_STATE["narrative"]'`
  to inject narrative into induced ptools at runtime
- finqa / calendar Class 3 had pydantic-ai recursion issues fixed in main
  pre-merge (commit a7df9a8)
- Class 3 val: pass induced ptools as `method=simulate` (not learned_code) —
  they live in `<learn_dir>/<ts>__ptool_inducer/learned_ptools.py`, not in the
  benchmark's standard ptool module
