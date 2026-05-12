# How to reproduce the Class 1 (ptool codedistill) results

## Models used

| role | opus | gemini |
|---|---|---|
| Learner (writes Python code) | `claude-opus-4-6` | `gemini/gemini-3.1-pro-preview` |
| Baseline simulate ptool (LLM in workflow) | `together_ai/deepseek-ai/DeepSeek-V3.1` (V3 for musr/rulearena) | unchanged |
| Backoff path (when generated code returns None) | same as baseline | same |

## End-to-end reproduce one benchmark

Replace `<bench>` with `bbh_sports`, `natural_plan`, `musr`, etc. Run from
the `secretagent/` repo root.

### Step 0: prerequisites

```bash
cd secretagent
set -a; source .env; set +a            # exposes ANTHROPIC_API_KEY / GEMINI_API_KEY / TOGETHER_AI_API_KEY
uv sync                                 # install deps
```

### Step 1: re-record train rollouts (one-time per benchmark)

```bash
cd benchmarks/<bench>
uv run python expt.py run --config-file conf/<bench>.yaml \
  dataset.partition=train dataset.n=100 \
  evaluate.expt_name=<bench>_train_full \
  evaluate.record_details=true evaluate.result_dir=recordings_full \
  llm.model=together_ai/deepseek-ai/DeepSeek-V3.1
```

### Step 2: distill with Opus (opus) OR Gemini (gemini)

```bash
# Opus version
uv run -m secretagent.cli.learn codedistill-all \
  --learned-dir learned_opus --model claude-opus-4-6 \
  --max-wrong-rate 0.20 \
  recordings_full/<latest>.<bench>_train_full

# Gemini version
uv run -m secretagent.cli.learn codedistill-all \
  --learned-dir learned_gemini --model gemini/gemini-3.1-pro-preview \
  --max-wrong-rate 0.20 \
  recordings_full/<latest>.<bench>_train_full
```

Both write `learned_<opus|gemini>/codedistill_config.yaml` listing ENABLED ptools.
After distill, `mv` outputs to this COMMON dir:

```bash
git mv learned_opus ../COMMON/codedistill-ptools-results/<bench>/learned_opus
```

### Step 3: end-to-end val on val split (Class 1)

```bash
PT_ARGS=$(python -c "import yaml; cfg=yaml.safe_load(open('learned_opus/codedistill_config.yaml')); [print(f'ptools.{n}.{k}={repr(v) if isinstance(v,bool) else v}') for n,kvs in cfg['ptools'].items() for k,v in kvs.items()]")

uv run python expt.py run --config-file conf/<bench>.yaml \
  dataset.partition=valid dataset.n=100 \
  evaluate.expt_name=<bench>_val_full_class1_opus \
  evaluate.record_details=true evaluate.result_dir=val_results_full \
  llm.model=together_ai/deepseek-ai/DeepSeek-V3.1 \
  $PT_ARGS \
  learn.train_dir=$PWD/learned_opus
```

### Step 4: end-to-end on test split

Same as Step 3 with `dataset.partition=test` (or `dataset.split=test` for
musr/bbh/medcalc/tabmwp; per-benchmark conventions vary).

## Full orchestration scripts

The full multi-benchmark orchestration scripts (used to produce the
paper-frozen results in this directory) live at:

- `benchmarks/jerry/class1_iters/run_class1_v4_full_codedistill.sh` (opus / Opus)
- `benchmarks/jerry/class1_iters/run_class1_v4g_gemini.sh` (gemini / Gemini)
- `benchmarks/jerry/class2_iters/run_v4g_vals_watcher.sh` (post-distill val watcher)
- `benchmarks/jerry/class2_iters/run_test_split_vals_all.sh` (test-split eval)

## Key parameters

| flag | default | what it does |
|---|---|---|
| `--max-wrong-rate` | 0.20 (was 0.05 in v2) | Max `val_wrong_rate` to ENABLE a ptool. opus raised from v2's 0.05 to capture more ptools |
| `--max-rounds` | 3 | LLM rewrite iterations per ptool |
| `--n-candidates` | 9 | Ensemble size per round |
| `--only-correct` | True | Only train from rollouts whose top-level answer was correct |
| `holdout_fraction` | 0.2 | Fraction of cases held out for `val_wrong_rate` gate (seed=42) |

## Notes on ENABLED-0 benchmarks

For some benchmarks (`bbh_geometric`, `bbh_date`, `medcalc`, `rulearena_*`),
both Opus and Gemini distills passed 0 ptools through the gate. Cause:
either code generation produced None-returning stubs (bbh_geometric, bbh_date,
rulearena), or all ptools' val_wrong_rate exceeded 20% on the small holdout
(medcalc). For these cells, Class 1 effectively == baseline.
