# AFlow rebuttal baseline (reviewer 5qsk W1)

External workflow-optimizer comparison: AFlow (Zhang et al., ICLR 2025; official
standalone repo) run on **Sports Understanding** and **FinQA** with splits,
subsets, and scoring matched exactly to the paper's cells.

- Executor: `gemini-2.5-flash-lite` (temperature 0) — matched across the AFlow
  arm and all reference cells.
- Optimizer: `gemini-3.1-pro-preview` (temperature 0).
- Search: `--sample 4 --max_rounds 15 --validation_rounds 3`, early stop when
  the top-3 mean is flat for 5 consecutive rounds (AFlow defaults otherwise).
- Selection on validation only; one frozen test pass per benchmark.

## Contents

| path | what |
|---|---|
| `RUNBOOK.md` | full chronological log: every run, failure, and deliberate deviation |
| `upstream/aflow_commit.txt` | upstream commit pinned (`3f45721`, 2025-12-25) |
| `upstream/aflow_changes.patch` | our complete diff to their tracked files (pricing, registration, operator set) |
| `upstream/benchmarks_finqa.py` | new FinQA benchmark class; scorer ported verbatim from `benchmarks/finqa/evaluator.py` |
| `upstream/test_pass.py` | held-out test runner (best-validation round -> `*_test.jsonl`) |
| `upstream/config2.yaml.redacted` | LLM endpoint config (Gemini OpenAI-compat), key redacted |
| `upstream/dataset_checksums.txt` | sha256 of the four exported JSONL datasets |
| `results/<bench>/workspace/` | seed + every generated round (graph.py/prompt.py), experience, per-round `results.json` |
| `results/test_logs/` | frozen test-pass CSVs (per-case rows) |
| `results/<bench>/*.log.gz` | full search logs (every LLM call with token/cost lines) |

## Reproduce from scratch

```bash
# 1. AFlow at the pinned commit, with our modifications
git clone https://github.com/FoundationAgents/AFlow && cd AFlow
git checkout $(cut -d' ' -f1 ../upstream/aflow_commit.txt)
git apply ../upstream/aflow_changes.patch
cp ../upstream/benchmarks_finqa.py benchmarks/finqa.py
cp ../upstream/test_pass.py .
uv venv -p 3.9 && uv pip install --python .venv/Scripts/python.exe -r requirements.txt requests
# config/config2.yaml from upstream/config2.yaml.redacted + your GEMINI_API_KEY

# 2. Datasets (bit-identical subsetting via the secretagent Dataset code path;
#    verify against upstream/dataset_checksums.txt)
uv run python scripts/export_aflow_datasets.py --aflow-dir <AFLOW_DIR>   # from secretagent root

# 3. Seed workspaces: copy results/<bench>/workspace/workflows/{template,round_1}
#    (these include the disclosed sports seed format instruction)

# 4. Search + frozen test (from AFLOW_DIR)
python run.py --dataset SportsUnderstanding --sample 4 --max_rounds 15 --validation_rounds 3 \
  --opt_model_name gemini-3.1-pro-preview --exec_model_name gemini-2.5-flash-lite
python run.py --dataset FinQA ...same flags...
python test_pass.py --dataset SportsUnderstanding
python test_pass.py --dataset FinQA

# 5. Reference cells (same executor, secretagent harness; from secretagent root)
bash scripts/run_gemlite_reference_cells.sh all

# 6. Tables
uv run benchmarks/COMMON/aflow-rebuttal/make_summary.py            # markdown
uv run benchmarks/COMMON/aflow-rebuttal/make_summary.py --format latex
```

## Deliberate deviations (also in RUNBOOK.md)

1. Sports round-1 seed carries a one-line answer-format instruction (canonical
   empty seed scores 0.00 under exact match -> degenerate search signal; every
   baseline arm's prompts contain equivalent format instructions).
2. FinQA operator set is `[Custom, ScEnsemble]`: `Programmer`'s code extractor
   returns nothing with this executor (verified standalone; model emits valid
   code in markdown fences), and `AnswerGenerate` does not exist in the math
   template. Both exclusions logged with evidence in RUNBOOK.md.
3. Held-out testing uses `test_pass.py` rather than `optimizer.test()` (which
   hardcodes `rounds=[1]` and a separate workflows_test tree).

## Cost-accounting caveat

The Gemini OpenAI-compat endpoint's usage field excludes `gemini-3.1-pro-preview`
thinking tokens, so the logged optimizer-side cost is an under-count. Executor
costs (flash-lite, non-thinking) are exact. See `make_summary.py` for how the
executor/optimizer split is derived.
