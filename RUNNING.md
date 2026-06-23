# Running experiments from the repo root

You can run any benchmark **from the top level of the repo** — no `cd` into a
task directory, and nothing is written back into the task dirs. This is the
preferred way to run the BBH and natural_plan "basics" grid and to reproduce
Table 1.

There are two entry points:

- **`secretagent.cli.expt`** — run *one* benchmark cell (one config + one
  strategy), from anywhere.
- **`secretagent.cli.basics`** — run the whole `model × task × strategy` grid,
  driven from the root, writing everything under `overall_results/`.

See also: [docs/CLI.md](docs/CLI.md) (full CLI reference),
[docs/CONFIG_KEYS.md](docs/CONFIG_KEYS.md) (config keys),
[benchmarks/HOWTO.md](benchmarks/HOWTO.md) (per-benchmark conventions).

---

## Prerequisites

- **uv** for running and dependency management (`uv sync` after a pull).
- **`.env`** at the repo root with `PATHTO_REPO` (already gitignored; see
  `.env-sample`). If absent, the root is auto-detected from the
  `.root-sentinel.txt` marker, so this is optional but recommended:

  ```
  PATHTO_REPO="C:/path/to/secretagent"
  ```

- **API keys** in the environment (or `.env`): `GEMINI_API_KEY`,
  `ANTHROPIC_API_KEY`, `TOGETHER_API_KEY`, etc. Integration runs cost real money.

All paths in the migrated configs resolve via `${oc.env:PATHTO_REPO}/...`, so a
config's cache / results / data locations are absolute and **cwd-independent**.

---

## Run a single cell from the root

```
uv run python -m secretagent.cli.expt run --config <path-to-conf.yaml> \
  [--evaluator MODULE.CLASS] [--interface MODULE.NAME] [DOTLIST_OVERRIDES...]
```

The task directory is derived from the config file's location: a config at
`<taskdir>/conf/<name>.yaml` means `<taskdir>` holds `ptools.py`, `data/`,
`prompt_templates/`, and `evaluator.py`. The runner puts `<taskdir>` on
`sys.path` and sets `pathto.task`, so `ptools`, the dataset, prompt templates,
and a task-local `--evaluator` all resolve automatically — from any cwd.

**BBH example** (default `ExactMatch` evaluator; `root_interface` comes from the
conf, so no `--interface` needed):

```
uv run python -m secretagent.cli.expt run \
  --config benchmarks/bbh/penguins_in_a_table/conf/conf.yaml \
  evaluate.expt_name=structured_baseline \
  ptools.answer_penguin_question.method=simulate
```

**natural_plan example** (task-local evaluator + a variant config):

```
uv run python -m secretagent.cli.expt run \
  --config benchmarks/natural_plan/trip/conf/trip.yaml \
  --evaluator evaluator.TripEvaluator \
  evaluate.expt_name=structured_baseline \
  ptools.trip_planning.method=simulate
```

Add `dataset.n=5` for a quick minibatch, and
`evaluate.result_dir=<somewhere>` to redirect output away from the task's own
`results/`.

> Running from *inside* a task dir still works unchanged (omit `--config`; it
> defaults to `conf/conf.yaml` relative to the cwd).

---

## Run the whole grid: `secretagent.cli.basics`

This driver reproduces each task's `make basics` targets across models, from the
root. It discovers a per-task **`strategies.yaml`** manifest under
`benchmarks/`, then runs each `model × task × strategy` cell as a subprocess.

### Discover what will run

```
uv run python -m secretagent.cli.basics list
```

### Dry run (print commands, execute nothing)

```
uv run python -m secretagent.cli.basics run --dry-run
```

### Run

```
uv run python -m secretagent.cli.basics run \
  [--models M1,M2] [--tasks IDS] [--strategies NAMES] \
  [--n N] [--out DIR] [--dry-run] [DOTLIST_OVERRIDES...]
```

| Option | Default | Description |
|---|---|---|
| `--models` | `gemini/gemini-3.1-pro-preview,gemini/gemini-2.5-flash-lite` | Comma-separated `llm.model` values |
| `--tasks` | all discovered | Comma-separated task ids, e.g. `bbh/penguins_in_a_table,natural_plan/trip` |
| `--strategies` | all in each manifest | Comma-separated strategy names |
| `--n` | full pool | `dataset.n` (minibatch size) |
| `--out` | `overall_results` | Output root for results |
| `--dry-run` | `false` | Print assembled commands without running |

Extra positional args become dotlist overrides applied to **every** cell, and
win over the driver's own (they are appended last). Example: bump react's
output-validation retries with a trailing `pydantic.retries=2`.

A cell that exits non-zero is recorded as failed in the summary and does **not**
abort the rest of the grid. Note: a model error *mid-eval* (e.g. a bad model id)
is caught per-case → recorded with NaN cost and scored wrong, while the cell
still exits `rc=0`. So model problems show up as low `correct` / NaN cost in the
summary, not as failed cells.

### Examples

```
# Quick smoke of the whole matrix (does every cell run?)
uv run python -m secretagent.cli.basics run --n 1

# One model, full pools, with extra retries for react
uv run python -m secretagent.cli.basics run \
  --models gemini/gemini-2.5-flash-lite pydantic.retries=2

# A single task across both default models
uv run python -m secretagent.cli.basics run --tasks bbh/sports_understanding
```

### Output layout

```
overall_results/
  <model_slug>/<task>/<strategy>/<timestamp>.<expt_name>/
      results.csv      # per-example predictions + correct/cost/tokens/latency
      config.yaml      # full strategy snapshot (provenance)
  summary.csv          # one row per cell: model, task, strategy, rc, correct, cost
```

`<model_slug>` is the model id with `/` → `_`. Nothing is written into the
benchmark/task dirs. Each task reuses its own LLM cache
(`benchmarks/<...>/<task>/llm_cache`, absolute in the conf), so reruns are cheap.

---

## Adding a task to the grid

Drop a `strategies.yaml` in the task dir (next to `ptools.py`). It is a faithful,
declarative copy of the task's Makefile `basics` targets:

```yaml
config: conf/conf.yaml              # relative to the task dir
evaluator: evaluator.TripEvaluator  # dotted; omit or null for ExactMatch
strategies:
  structured_baseline:
    - ptools.trip_planning.method=simulate
  workflow:
    - ptools.trip_planning.method=direct
    - ptools.trip_planning.fn=ptools.trip_workflow
```

The driver discovers it on the next `list`/`run`. The task id is its path under
`benchmarks/` (e.g. `natural_plan/trip`).

---

## Running in parallel (important: partition by task)

The driver runs cells **sequentially** within one invocation. To go faster, run
**multiple invocations partitioned by task** — never split one task across
processes.

**Why task-level only:** each task has its own `llm_cache/` dir, but cachier's
cross-process cache invalidation is deliberately disabled (see
[cache_util.py](src/secretagent/cache_util.py)). Two processes writing the
**same** task's cache dir will clobber each other's writes or corrupt the cache.
Different *tasks* have disjoint cache dirs, so they are safe to run concurrently.
Splitting one task's models/strategies across processes is **not** safe.

```
# safe: one process per task (disjoint caches)
uv run python -m secretagent.cli.basics run --tasks bbh/date_understanding   ... &
uv run python -m secretagent.cli.basics run --tasks bbh/geometric_shapes     ... &
uv run python -m secretagent.cli.basics run --tasks bbh/penguins_in_a_table  ... &
uv run python -m secretagent.cli.basics run --tasks bbh/sports_understanding ... &
```

Two caveats for parallel runs:

- **`summary.csv` collides.** Result subdirs are unique per
  `(model, task, strategy, timestamp)`, so no result data is lost — but every
  invocation overwrites `<out>/summary.csv`. Either give each process its own
  `--out` and merge, or re-aggregate the summary from the result tree after all
  processes finish.
- **Rate limits.** More concurrent streams → more provider 429/503 throttling.
  Transients are retried with backoff, but keep concurrency modest.

---

## Models

The default pair is **`gemini/gemini-3.1-pro-preview`** (best/newest) and
**`gemini/gemini-2.5-flash-lite`** (cheapest). Override with `--models`.

> Note: the bare id `gemini/gemini-3.1-pro` returns a litellm **404** — the
> 3.1-pro tier resolves only under `gemini/gemini-3.1-pro-preview`. Other
> verified-working ids: `gemini-2.5-pro`, `gemini-2.5-flash`,
> `gemini-2.5-flash-lite`, `gemini-3.1-flash-lite`.

The pricier/thinking models (pro tier) are dramatically slower and costlier on
the multi-call strategies (`workflow`, `pot`, `react`) than on the baselines —
budget accordingly, and prefer a `--n` minibatch when iterating.