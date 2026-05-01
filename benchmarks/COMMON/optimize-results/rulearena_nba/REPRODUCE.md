# Reproducing the NBA cache-effectiveness experiment

This directory is a frozen snapshot of one NSGA-II sweep on RuleArena NBA, the cache state it was run against, and the analysis of how much the cache absorbed.

## What's here

| Path | Description |
|---|---|
| `CACHE_FINDINGS.md` | Written analysis: headline numbers, per-generation trend, caveats |
| `nsga2_summary.csv` | One row per evaluated config — `correct`, `cost`, `frontier`, `valid` |
| `nsga2_generations.csv` | Per-generation stats — frontier size, new evals, cache hits, elapsed |
| `nsga2.png` | Cost-vs-accuracy scatter with Pareto frontier highlighted |
| `plot.py` | Regenerates `nsga2.png` from `nsga2_summary.csv` (uses shared `secretagent.optimize.viz`) |
| `nsga_runs/nsga_001/ … nsga_043/` | Per-config result dirs — `config.yaml`, `results.csv`, `results.jsonl` |
| `baselines/baseline_*/` | Six-model baseline runs (Pareto reference for the sweep) |

## Where the cache lives (not in this directory)

The LLM cache is at **`benchmarks/rulearena/nba/llm_cache/`** in the repo. It contains two cachier shelve files:

```
benchmarks/rulearena/nba/llm_cache/
├── .secretagent.implement.pydantic._run_agent_impl   # top-level Agent calls (simulate_pydantic)
└── .secretagent.llm_util._llm_impl                    # leaf LLM calls (simulate, prompt_llm)
```

These are committed alongside the artifact so cost numbers can be verified bit-exact.

## Verify the headline numbers

```bash
# from repo root
git checkout <commit>
uv sync

# 1. CACHE_AFTER — must run from nba/, otherwise cli.costs silently skips the
#    Agent cache file because pickled entries reference the local `ptools` module
#    (cache_util.py:128 swallows the ModuleNotFoundError).
cd benchmarks/rulearena/nba
uv run -m secretagent.cli.costs llm_cache
# expected: cost ~$33.43, ~1490 calls

# 2. NOCACHE — sum cost across all 43 NSGA-II per-config CSVs
cd ../../../benchmarks/COMMON/optimize-results/rulearena_nba
uv run python -c "
import pandas as pd, pathlib
csvs = sorted(pathlib.Path('nsga_runs').glob('nsga_*/results.csv'))
total = sum(pd.read_csv(f)['cost'].sum() for f in csvs)
print(f'NOCACHE = \${total:.4f}  ({len(csvs)} configs)')
"
# expected: NOCACHE ~$95.44, 43 configs

# 3. Per-generation cache-hit trend (config-level)
cat nsga2_generations.csv
# expected: hit_pct rises 0% -> 9% -> 30% -> 55% -> 58% -> 56%

# 4. Regenerate the Pareto plot
uv run plot.py
# writes nsga2.png alongside this file; uses log-x scale for the
# 100x cost range and dedupes identical (config, acc, cost) rows.
```

CACHE_BEFORE_NSGA2 ($21.53) is recorded in `CACHE_FINDINGS.md`. It cannot be re-derived from the current cache state alone — the cache has grown since. To re-derive: revert the two cache files to their state at the post-baseline commit and run `cli.costs` again. (Bit-exact reproduction below uses the values as-recorded.)

## Re-running the sweep end-to-end (optional)

The sweep itself can be re-run; results will match within float jitter, the per-generation hit-rate trend should be qualitatively identical.

```bash
# baselines (one model at a time)
cd benchmarks/rulearena/nba
for model in \
  "together_ai/deepseek-ai/DeepSeek-V3" \
  "together_ai/deepseek-ai/DeepSeek-V3.1" \
  "together_ai/openai/gpt-oss-20b" \
  "together_ai/openai/gpt-oss-120b" \
  "gemini/gemini-2.5-flash" \
  "gemini/gemini-2.5-flash-lite"; do
  uv run python -m secretagent.cli.expt run \
    --interface ptools.compute_nba_answer \
    --evaluator evaluator.NbaEvaluator \
    ptools.compute_nba_answer.method=simulate_pydantic \
    ptools.compute_nba_answer.tool_module=__learned__ \
    ptools.compute_nba_answer.learner=ptool_inducer \
    ptools.compute_nba_answer.tools=__all__ \
    learn.train_dir=learned \
    llm.model=$model \
    evaluate.expt_name="baseline_${model##*/}"
done

# NSGA-II sweep
cd benchmarks/rulearena
uv run -m secretagent.cli.optimize nsga2 \
  --space-file nsga2_nba.yaml --cwd nba \
  --pop-size 12 --n-gen 5 --timeout 1200 \
  dataset.n=50
```

Required env vars: `TOGETHER_API_KEY`, `GEMINI_API_KEY`. The induced ptools the sweep uses live at `benchmarks/rulearena/nba/learned/20260416.200721.compute_nba_answer__ptool_inducer/`.

## Caveats

See `CACHE_FINDINGS.md` for full discussion. Briefly:
- 4% of case-rows have NaN cost (Windows-specific litellm async teardown crash; data on disk is fine).
- Five configs hit the 1200s wall-clock timeout.
- One PoT config genuinely failed at 7.1% — known pydantic/dict asymmetry, tracked separately.
