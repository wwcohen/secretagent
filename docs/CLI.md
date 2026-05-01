# CLI Commands

All CLI tools live in `src/secretagent/cli/` and are run with `uv run -m`.

## secretagent.cli.bench

Universal benchmark runner. Dispatches to per-benchmark runners as subprocesses.

### list

Show all registered benchmarks with eval pool and minibatch sizes.

```
uv run -m secretagent.cli.bench list
```

### run

Run a single benchmark evaluation.

```
uv run -m secretagent.cli.bench run BENCHMARK [--minibatch] [DOTLIST_OVERRIDES...]
```

| Option | Description |
|---|---|
| `BENCHMARK` | Benchmark name from registry (e.g. `sports_understanding`, `medcalc`) |
| `--minibatch` | Use the default minibatch size for quick evaluation |

Extra positional args are passed as dotlist config overrides to the benchmark runner.

### run-all

Run all registered benchmarks sequentially.

```
uv run -m secretagent.cli.bench run-all [--minibatch] [DOTLIST_OVERRIDES...]
```

## secretagent.cli.costs

Summarize LLM costs from cachier cache files.

```
uv run -m secretagent.cli.costs [CACHE_DIR] [--config-file FILE]
```

| Argument/Option | Description |
|---|---|
| `CACHE_DIR` | Path to cachier cache directory (optional) |
| `--config-file` | YAML config file to load (uses `cachier.cache_dir` from config) |

Prints total and per-call statistics for input/output tokens, latency, and cost.

## secretagent.cli.results

Analyze experiment results saved by savefile. Experiment directories (or CSV files within them) are passed as extra positional arguments after the subcommand. Results are filtered with `--latest` and `--check`.

### list

Show available experiment directories and row counts.

```
uv run -m secretagent.cli.results list [--latest K] [--check KEY=VALUE] DIRS...
```

### average

Report mean +/- stderr of metrics, grouped by experiment.

```
uv run -m secretagent.cli.results average [--latest K] [--check KEY=VALUE] [--metric NAME] [--pareto] DIRS...
```

Default metric is `cost`. Multiple `--metric` flags are supported. Append `-` to a metric name to indicate it should be minimized (e.g. `--metric cost-`); by default metrics are maximized. Use `--pareto` to show only Pareto-optimal experiments.

### pair

Run paired t-tests on metrics across experiments (requires at least 2 experiments).

```
uv run -m secretagent.cli.results pair [--latest K] [--check KEY=VALUE] --metric NAME DIRS...
```

At least one `--metric` is required. Metric names may have a `-` suffix (stripped before lookup).

### plot

Plot experiments as points on two metrics with error boxes.

```
uv run -m secretagent.cli.results plot [--latest K] [--check KEY=VALUE] --metric NAME --metric NAME [--pareto] [--output FILE] DIRS...
```

Exactly two `--metric` options are required. Each experiment is rendered as a point at (mean_metric1, mean_metric2) with a rectangle showing +/- 1 stderr. Pareto-optimal experiments are marked with stars; others with circles. Use `--pareto` to show only Pareto-optimal experiments.

| Option | Default | Description |
|---|---|---|
| `--output` | `results_plot.png` | Output PNG file path |
| `--pareto` | `false` | Only show Pareto-optimal experiments |

### compare-configs

Show configuration differences between experiments.

```
uv run -m secretagent.cli.results compare-configs [--latest K] [--check KEY=VALUE] DIRS...
```

### validate

Check that experiment directories contain required files (`config.yaml`, `results.csv` by default).

```
uv run -m secretagent.cli.results validate [--latest K] [--check KEY=VALUE] [--require FILE] [--norequire FILE] [--purge] DIRS...
```

| Option | Description |
|---|---|
| `--require` | Add an additional required file |
| `--norequire` | Remove a default required file |
| `--purge` | Interactively delete directories that fail validation |

### delete-obsolete

Delete experiment directories not retained by `filter_paths`.

```
uv run -m secretagent.cli.results delete-obsolete [--latest K] [--check KEY=VALUE] DIRS...
```

Lists directories to keep and delete, then prompts for confirmation.

### export

Copy filtered result directories to `benchmarks/results/<relative_path>`.

```
uv run -m secretagent.cli.results export [--latest K] [--check KEY=VALUE] [--as RELATIVE_PATH] DIRS...
```

Run from a benchmark directory (e.g. `benchmarks/bbh/sports_understanding`). Copies each filtered result directory to `benchmarks/results/<path_from_benchmarks>/`. Use `--as` to override the relative path.

| Option | Default | Description |
|---|---|---|
| `--as` | auto-detected from cwd | Override relative path under `benchmarks/results/` |

Existing directories at the destination are skipped.

### Metric direction

Any `--metric` flag across `average`, `pair`, and `plot` can have a `-` suffix to indicate the metric should be minimized rather than maximized (e.g. `--metric cost-`). This affects Pareto optimality calculations and sort order.

### Common options

| Option | Default | Description |
|---|---|---|
| `--latest K` | 1 | Keep latest K directories per tag; 0 for all |
| `--check KEY=VALUE` | — | Config constraint filter (repeatable) |
| `--config-file FILE` | — | YAML config file to load |

## secretagent.cli.expt

Generic benchmark experiment runner. Run from a benchmark directory that contains `conf/conf.yaml`, a `data/` subdirectory, and a `ptools` module.

### run

Run a benchmark evaluation.

```
uv run python -m secretagent.cli.expt run --interface MODULE.NAME [--evaluator MODULE.CLASS] [DOTLIST_OVERRIDES...]
```

| Option | Description |
|---|---|
| `--interface` | (required) Top-level interface as `module.name`, e.g. `ptools.my_fn` |
| `--evaluator` | Evaluator class as `module.ClassName` (default: `ExactMatchEvaluator`) |

Extra args are parsed as config overrides in dot notation.

### quick-test

Run the top-level interface on a single example with full tracing.

```
uv run python -m secretagent.cli.expt quick-test --interface MODULE.NAME [DOTLIST_OVERRIDES...]
```

## secretagent.cli.optimize

Grid search and multi-objective optimization over configuration spaces. See [optimizer.md](optimizer.md) for full documentation.

### sweep

Run a grid search from a YAML search space definition.

```
uv run -m secretagent.cli.optimize sweep \
  --command "uv run python expt.py run --config-file conf/murder.yaml" \
  --space-file sweep_space.yaml \
  [--cwd DIR] [--timeout SECS] [--metric NAME] [--output FILE] \
  [DOTLIST_OVERRIDES...]
```

| Option | Default | Description |
|---|---|---|
| `--command` | (required) | Base command to run (quoted) |
| `--space-file` | (required) | YAML file defining search space |
| `--prefix` | `sweep` | Experiment name prefix |
| `--cwd` | current dir | Working directory for subprocesses |
| `--timeout` | `1800` | Timeout per config in seconds |
| `--metric` | `correct` | Metric column to optimize |
| `--output` | `sweep_summary.csv` | Output summary CSV |

### nsga2

Run NSGA-II multi-objective search over a modular config space. See [optimizer.md](optimizer.md#nsga-ii-multi-objective-search) for details.

```
uv run -m secretagent.cli.optimize nsga2 \
  --space-file nsga2.yaml [--cwd DIR] [--pop-size N] [--n-gen N] \
  [--timeout SECS] [--metric NAME] [--dry-run] [DOTLIST_OVERRIDES...]
```

### run-all

Run NSGA-II across multiple benchmarks sequentially.

```
uv run -m secretagent.cli.optimize run-all [-b BENCHMARK] [--pop-size N] [--n-gen N] [DOTLIST_OVERRIDES...]
```

Registered benchmarks: `airline`, `nba`, `tax`, `finqa`, `medcalc`, `tabmwp`, `sports`. Defaults to all. Auto-runs `cross-summary` on completion.

### cross-summary

Cross-benchmark comparison from multiple NSGA-II runs.

```
uv run -m secretagent.cli.optimize cross-summary \
  airline/results/nsga2_summary.csv nba/results/nsga2_summary.csv [--metric NAME] [--output FILE]
```

| Option | Default | Description |
|---|---|---|
| `--metric` | `correct` | Metric column name |
| `--ref-cost` | auto | Reference cost for hypervolume |
| `--output` | none | Save markdown table to file |

### summary

Display results from a saved sweep.

```
uv run -m secretagent.cli.optimize summary SWEEP_RESULTS.csv [--top-n N]
```

## secretagent.cli.learn

Learn implementations from recorded interface calls.

### induce-ptools

Induce ptool specs from recorded agent thoughts via a 4-stage LLM pipeline: load thoughts → LLM-categorize → merge synonyms → LLM-synthesize ptool specs. Produces `learned_ptools.py` with `@implement_via('simulate')` stubs + `implementation.yaml` with `method=simulate_pydantic, tool_module=__learned__`.

```
uv run -m secretagent.cli.learn induce-ptools \
  --interface NAME --task-desc TEXT [--trace-mode react|cot] \
  [--state-injection EXPR] [--only-correct] [--max-ptools N] \
  [--min-count N] [--model MODEL] [--latest K] [--check KEY=VALUE] \
  [--learned-dir DIR] DIRS...
```

| Option | Description |
|---|---|
| `--interface` | Top-level interface whose traces are being induced from |
| `--task-desc` | Natural-language task description (goes into categorize/synthesize prompts) |
| `--trace-mode` | `react` extracts `step_info[].thought`; `cot` chunks `rollout[0].output` |
| `--state-module` | Python module to import state dict from, e.g. `ptools_common` |
| `--state-expr` | Expression evaluated at call time, e.g. `_REACT_STATE["narrative"]`. Both `--state-module` and `--state-expr` must be set together. |
| `--only-correct` | Only use correct rollouts (success-only induction) |
| `--max-ptools` | Max ptools to synthesize (default 5) |
| `--min-count` | Min category count to synthesize (default 3) |
| `--model` | LLM model (default `together_ai/deepseek-ai/DeepSeek-V3`) |
| `--learned-dir` | Where to save outputs (default `learned`) |

Once induced, eval via::

    ptools.NAME.method=simulate_pydantic \
    ptools.NAME.tool_module=__learned__ \
    ptools.NAME.learner=ptool_inducer \
    ptools.NAME.tools=__all__ \
    learn.train_dir=learned

### rote

Collect training data for a rote (lookup-based) learner from recorded interface calls.

```
uv run -m secretagent.cli.learn rote --interface NAME [--latest K] [--check KEY=VALUE] [--train-dir DIR] DIRS...
```

| Option | Default | Description |
|---|---|---|
| `--interface` | (required) | Interface name to extract, e.g. `consistent_sports` |
| `--latest K` | 1 | Keep latest K directories per tag; 0 for all |
| `--check KEY=VALUE` | — | Config constraint filter (repeatable) |
| `--train-dir DIR` | `/tmp/rote_train` | Directory to store collected training data |
