# Oolong Benchmark

Minimal commands for running Oolong experiments.

## Data layout

Expected shard files:
- `data/validation/{context_len}.jsonl`
- `data/test/{context_len}.jsonl`

Example context lengths: `1024, 2048, 4096, 8192, 16384, 32768`.

## Run

```bash
cd benchmarks/oolong

# Smoke run (5 examples, validation 1024)
uv run python expt.py run dataset.split=validation dataset.context_len=1024 dataset.n=5

# Full shard run (all examples in split/context)
uv run python expt.py run dataset.split=test dataset.context_len=1024 dataset.n=null

# Force fresh run (no llm cache, no window cache)
uv run python expt.py run dataset.context_len=1024 cachier.enable_caching=false oolong.enable_window_cache=false
```

Top-level evaluated interface is `ptools.answer_question` (bound to `direct` by default).

## Common overrides

```bash
# Parallel workers
oolong.max_workers=4

# Answer method (simulate_pydantic or program_of_thought)
ptools.answer_from_cached_records.method=simulate_pydantic

# Per-run tag
evaluate.expt_name=my_run_name
```

## Outputs

Runs are written under:
- `results/{context_len}/{timestamp}.{expt_name}/`

Useful files:
- `results.csv`, `results.jsonl`
- `classification_accuracies.json`
- `classification_results.json`
