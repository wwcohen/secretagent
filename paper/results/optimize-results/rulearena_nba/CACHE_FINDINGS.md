# NBA cache-effectiveness experiment

**Date:** 2026-05-01
**Benchmark:** RuleArena NBA, `compute_nba_answer`, dataset.split=valid, n=42 (test) / n=50 (sweep)
**Sweep:** NSGA-II, pop_size=12, n_gen=5, timeout=1200s, 4 search dimensions (toplevel_method × llm.model × extract_nba_params.method × extract_nba_params.model)

## Headline

The cachier-backed LLM cache absorbed **87.5%** of total NSGA-II API spend.

| metric | value |
|---|---|
| CACHE_BEFORE_NSGA2 | $21.5297 |
| CACHE_AFTER | $33.4303 |
| MISSES (fresh API) | $11.9006 |
| NOCACHE (sum cost across NSGA-II CSVs) | $95.4397 |
| HITS | $83.5391 |
| **HitRate = HITS / NOCACHE** | **87.5%** |

`CACHE_BEFORE_NSGA2` is the cache total after the 6-model baseline + smoke test, before the production NSGA-II run. `CACHE_AFTER` is measured after the run finishes. `NOCACHE` is the cost the run would have paid with no cache, computed by summing `cost` across each per-config `results.csv` (which records the at-call cost regardless of cache state).

## Per-generation trend (config-level)

NSGA-II skips configs already in its evaluation history. The fraction of considered configs that were already-seen rises monotonically with generation, then plateaus:

| gen | new evals | cache hits | considered | hit% |
|---|---|---|---|---|
| 0 | 12 | 0 | 12 | 0.0% |
| 1 | 10 | 1 | 11 | 9.1% |
| 2 | 7 | 3 | 10 | 30.0% |
| 3 | 5 | 6 | 11 | 54.5% |
| 4 | 5 | 7 | 12 | 58.3% |
| 5 | 4 | 5 | 9 | 55.6% |

By generation 3 the population has converged enough that more than half of NSGA-II's proposed configs are repeats. This validates the hypothesis: the optimizer revisits good configs as it converges, and the cache turns that revisitation into near-zero API cost.

The aggregate 87.5% hit rate is higher than the config-level numbers above because most of the savings come from sub-call cache hits (the inner ptools call into `simulate` factories whose `(prompt, model)` keys repeat across configs that share a sub-interface).

## Baseline Pareto reference

Six-model react_learned baseline on 42 NBA test cases (Pareto reference for the sweep):

| model | acc | top-level cost (sum) |
|---|---|---|
| DeepSeek-V3 | 90.5% | $12.4636 |
| gemini-2.5-flash | 78.6% | $1.6350 |
| DeepSeek-V3.1 | 76.2% | $5.8970 |
| gpt-oss-20b | 73.8% | $0.0945 |
| gpt-oss-120b | 71.4% | $0.2813 |
| gemini-2.5-flash-lite | 31.0% | $0.1399 |

`gemini-2.5-flash-lite` at 31% accuracy is a degraded baseline — likely struggles with the structured tool-call schema for the induced ptools. Kept in the search space for Pareto diversity at the cheap end.

## Reproduction

Bit-exact reproduction (intended path): the cache directory and result directories are shipped together with the paper artifact.

```bash
# from secretagent repo root
git checkout <commit>
uv sync
cd benchmarks/rulearena/nba

# verify CACHE_AFTER (must run from this dir; from repo root the Agent cache file
# is silently skipped due to a swallowed ModuleNotFoundError in cache_util.py:128)
uv run -m secretagent.cli.costs llm_cache
# expected: cost ~$33.43, 1490+ calls

# verify NOCACHE
uv run python -c "
import pandas as pd, pathlib
csvs = sorted(pathlib.Path('results').glob('*nsga_*/results.csv'))
print(f'NOCACHE = \${sum(pd.read_csv(f)[\"cost\"].sum() for f in csvs):.4f} ({len(csvs)} configs)'
)"
# expected: NOCACHE ~$95.44, 43 configs

# verify per-generation trend
cat results/nsga2_generations.csv
```

End-to-end reproduction (without shipped cache): re-run the 6-model baseline loop and the NSGA-II command from `nba/`. Expected within float jitter of the same totals; per-generation hit rate trend should be qualitatively identical.

## Caveats

- 74 of 1806 case-rows (4.1%) have NaN cost. These are configs that crashed during process teardown on Windows — the eval work and partial CSV both finished, but litellm's async logger triggered a STATUS_ACCESS_VIOLATION in shutdown. Data is intact on disk; NSGA-II treats them as failed which slightly biases Pareto exploration but does not affect the cache math (NaN costs simply don't contribute to NOCACHE). Not a Linux/Docker issue.
- Five configs hit the 1200s wall-clock timeout. Their results.csv contains zero or partial rows and contributes correspondingly less to NOCACHE; cache contribution from whatever LLM calls completed before timeout is preserved.
- One PoT config genuinely failed at 7.1% accuracy — the deferred pydantic/dict asymmetry bug in `extract_nba_params -> NbaResult` (LLM-generated code uses dict-style access on a pydantic model). Tracked for post-experiment fix.
- The earlier `$20.9795` measurement of CACHE_BEFORE was an undercount: `cli.costs` from repo root silently skipped the `_run_agent_impl` cache file due to an unimportable `ptools` reference in pickled entries. Always run `cli.costs` from the benchmark dir.
