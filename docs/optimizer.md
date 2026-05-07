# Optimizer

Two search strategies for finding good configurations:

- **Grid search** (`sweep`): exhaustive enumeration over a YAML-defined space.
  Best for small, flat spaces (e.g., 2 methods × 3 models = 6 configs).
- **NSGA-II** (`nsga2`): evolutionary multi-objective search over a modular
  space. Finds Pareto-optimal tradeoffs between accuracy and cost. Best for
  large compositional spaces (thousands of configs).

Both evaluate each config as a subprocess to ensure clean module state.

---

# NSGA-II Multi-Objective Search

## Concept

In a modular agentic system, each sub-interface (e.g., `extract_params`,
`compute_calculator`) can use a different method and model. An NSGA-II
*individual* encodes a complete workflow configuration as an integer
vector — one gene per decision. The algorithm searches for configurations
that are **Pareto-optimal**: no other config is both more accurate and
cheaper.

## Modular Search Space

Each domain defines a search space in `benchmarks/rulearena/search_spaces.py`.
A space function returns `(dims, compound_overrides)`:

- **dims**: list of `SearchDimension`, each with a key and list of values.
  One integer gene per dimension.
- **compound_overrides**: dimensions where one gene value expands to
  multiple dotlist overrides (e.g., `toplevel_method="pot"` → 4 overrides).

### Example: Airline (6 genes, 4,320 configs)

| Gene | Key | Values | Type |
|------|-----|--------|------|
| 0 | `toplevel_method` | structured_baseline, unstructured_baseline, workflow, pot, react | compound |
| 1 | `llm.model` | DSv3, DSv3.1, GPToss20B, GPToss120B, Qwen9B, Gemma3n | simple |
| 2 | `extract_airline_params.method` | simulate_pydantic, simulate | simple |
| 3 | `extract_airline_params.model` | (same 6 models) | simple |
| 4 | `compute_airline_calculator.method` | direct, simulate | simple |
| 5 | `compute_airline_calculator.model` | (same 6 models) | simple |

Chromosome `[4, 1, 1, 3, 0, 5]` means: react top-level with DSv3.1 globally,
extract via simulate with GPToss120B, calculator via direct with Gemma3n.

### Domain Summary

| Domain | Sub-interfaces | Methods | Genes | Space |
|--------|---------------|---------|-------|-------|
| airline | extract + calculator | 5 | 6 | 4,320 |
| nba | extract only | 5 | 4 | 360 |
| tax | extract + calculator | 6 | 6 | 5,184 |

## Defining a Search Space (YAML)

Create a YAML file with three sections:

```yaml
# nsga2_airline.yaml
interface: ptools.compute_airline_answer    # used to build subprocess command
evaluator: evaluator.AirlineEvaluator       # optional

models:                                     # shared model pool
  - together_ai/deepseek-ai/DeepSeek-V3
  - together_ai/openai/gpt-oss-20b
  - together_ai/google/gemma-3n-E4B-it

methods:                                    # top-level method → dotlist overrides
  structured_baseline:
    - ptools.compute_airline_answer.method=simulate
  workflow:
    - ptools.compute_airline_answer.method=direct
    - ptools.compute_airline_answer.fn=ptools.airline_workflow
  pot:
    - ptools.compute_airline_answer.method=program_of_thought
    - ptools.compute_airline_answer.tools=[ptools.extract_airline_params,ptools.compute_airline_calculator]
    - ptools.compute_airline_answer.inject_args=true
    - llm.max_tokens=16384

sub_interfaces:                             # per-interface method + model genes
  ptools.extract_airline_params:
    methods: [simulate_pydantic, simulate]
  ptools.compute_airline_calculator:
    methods: [direct, simulate]
```

The builder auto-generates genes: `toplevel_method` (compound) + `llm.model` +
per-sub-interface method and model genes.

## Running NSGA-II

### YAML mode (recommended)

```bash
# Dry run — verify commands, no API calls
uv run -m secretagent.cli.optimize nsga2 \
    --space-file nsga2_airline.yaml --cwd airline --dry-run dataset.n=10

# Real run
uv run -m secretagent.cli.optimize nsga2 \
    --space-file nsga2_airline.yaml --cwd airline \
    --pop-size 12 --n-gen 5 --timeout 600 dataset.n=20
```

### RuleArena examples (from `benchmarks/rulearena/`)

```bash
# Airline (6 genes, 4,320 configs)
uv run -m secretagent.cli.optimize nsga2 \
    --space-file nsga2_airline.yaml --cwd airline \
    --pop-size 12 --n-gen 5 dataset.n=20

# NBA (4 genes, 360 configs)
uv run -m secretagent.cli.optimize nsga2 \
    --space-file nsga2_nba.yaml --cwd nba \
    --pop-size 12 --n-gen 5 dataset.n=20

# Tax (6 genes, 5,184 configs)
uv run -m secretagent.cli.optimize nsga2 \
    --space-file nsga2_tax.yaml --cwd tax \
    --pop-size 12 --n-gen 5 dataset.n=20
```

### FinQA example (from `benchmarks/finqa/`)

```bash
uv run -m secretagent.cli.optimize nsga2 \
    --space-file nsga2.yaml --pop-size 12 --n-gen 5 dataset.n=50
```

### Python mode (alternative)

If you need programmatic control, use `--space` with a Python function:

```bash
uv run -m secretagent.cli.optimize nsga2 \
    --interface ptools.compute_airline_answer \
    --evaluator evaluator.AirlineEvaluator \
    --space search_spaces.airline_modular_space \
    --cwd airline dataset.n=20
```

### Key options

| Option | Default | Description |
|--------|---------|-------------|
| `--space-file` | none | YAML space definition (recommended) |
| `--space` | none | Python space function as `module.func` |
| `--interface` | from YAML | Top-level interface |
| `--evaluator` | from YAML | Evaluator class |
| `--cwd` | `.` | Working directory for subprocesses |
| `--pop-size` | 12 | Population size (rounded up to multiple of 4) |
| `--n-gen` | 5 | Number of generations |
| `--timeout` | 600 | Timeout per config (seconds) |
| `--metric` | `correct` | Metric to maximize |
| `--seed` | 42 | Random seed |
| `--dry-run` | false | Print sample commands without running |
| `--no-plot` | false | Skip Pareto plot |

Extra positional args are dotlist config overrides applied to every config.

### Adding a new benchmark

1. Create `nsga2.yaml` in the benchmark directory
2. List models, methods (with dotlist overrides), and sub-interfaces
3. Run with `--space-file nsga2.yaml`

No Python code needed.

## Interpreting Results

### Pareto frontier

The output reports which configs are non-dominated:

```
PARETO FRONTIER (27 valid / 39 evaluated)
  Config                              correct     Cost/q
  workflow/GPToss20B                  100.0% $   0.0042
  structured_baseline/Gemma3n           0.0% $   0.0013
```

A config is Pareto-optimal if no other config has both higher accuracy
and lower cost. Failed configs (timeout, NaN, crash) are scored as
(0% accuracy, infinite cost) and excluded.

### Hypervolume

Compare frontier quality across runs using the hypervolume indicator:

```bash
cd benchmarks/rulearena/airline
uv run -m secretagent.cli.results hypervolume --latest 0 \
    --metric correct --metric cost- results/*nsga*
```

Larger hypervolume = better frontier. Use `--ref` with a fixed reference
point to compare across different result sets.

### Running all benchmarks at once

```bash
# All registered benchmarks
uv run -m secretagent.cli.optimize run-all --pop-size 12 --n-gen 5 dataset.n=20

# Specific benchmarks only
uv run -m secretagent.cli.optimize run-all -b airline -b nba dataset.n=20

# Dry run to verify commands
uv run -m secretagent.cli.optimize run-all --dry-run
```

This runs NSGA-II sequentially for each benchmark and auto-generates a
cross-benchmark summary at the end.

### Cross-benchmark comparison

After running NSGA-II on multiple benchmarks, compare them side by side:

```bash
cd benchmarks/rulearena
uv run -m secretagent.cli.optimize cross-summary \
    airline/results/nsga2_summary.csv \
    nba/results/nsga2_summary.csv \
    tax/results/nsga2_summary.csv
```

This reports per-benchmark frontier size, best accuracy, cheapest cost,
and hypervolume, plus method/model frequency across all frontiers.
Use `--output table.md` to save a markdown table for the paper.

## How It Works

1. **Encode**: each config = integer vector (one index per dimension)
2. **Decode**: `decode_modular()` expands compound dimensions, produces
   dotlist overrides
3. **Evaluate**: subprocess runs `secretagent.cli.expt run` with overrides;
   results cached by chromosome
4. **Evolve**: NSGA-II with uniform crossover + random reset mutation
   over categorical genes; `selNSGA2` for survivor selection
5. **Report**: Pareto frontier + cost-vs-accuracy plot

The search auto-selects exhaustive enumeration when the space has
≤20 configs, NSGA-II otherwise.

## Module Structure

```
src/secretagent/
    optimize/
        encoder.py        # SearchDimension, decode, decode_modular,
                          #   modular_space_from_yaml
        pareto.py          # EvalCache, run_exhaustive, run_nsga2
        metrics.py         # compute_hypervolume, compare_hypervolumes
        viz.py             # plot_pareto_frontier
    cli/
        optimize.py        # CLI: sweep, nsga2, cross-summary, summary

benchmarks/<name>/
    nsga2.yaml             # YAML space definition (portable)
    search_spaces.py       # Python space functions (optional)
```

---

# Grid Search Optimizer

The grid search (`sweep`) exhaustively enumerates a YAML-defined space.
Best for small, flat spaces.

## Architecture

```
              ┌──────────────────────────┐
              │  User provides:          │
              │  - base command          │
              │  - search space (YAML)   │
              │  - base dotlist overrides │
              └─────────┬────────────────┘
                        │
              ┌─────────▼────────────────┐
              │  ConfigSpace              │
              │  Generates all combos     │
              │  via itertools.product    │
              └─────────┬────────────────┘
                        │
              ┌─────────▼────────────────┐
              │  GridSearchRunner         │
              │  For each config point:   │
              │  1. Run subprocess        │
              │  2. Parse accuracy        │
              │  3. Load CSV for stats    │
              └─────────┬────────────────┘
                        │
              ┌─────────▼────────────────┐
              │  Summary DataFrame        │
              │  Ranked by accuracy       │
              │  With cost/latency/tokens │
              └──────────────────────────┘
```

Each config runs as an independent subprocess (`uv run python expt.py
run ...`), which guarantees clean module state. This is necessary
because `@interface` decorators modify global state that cannot be
reset in-process.

## Quickstart

### 1. Define a search space (YAML)

```yaml
# sweep_space.yaml
variants:
  evaluate.entry_point:
    - answer_question
    - answer_question_workflow
  llm.thinking:
    - "true"
    - "false"
  llm.model:
    - together_ai/deepseek-ai/DeepSeek-V3
    - claude-haiku-4-5-20251001
```

### 2. Run the sweep

```bash
uv run -m secretagent.cli.optimize sweep \
  --command "uv run python expt.py run --config-file conf/murder.yaml" \
  --space-file sweep_space.yaml \
  --cwd benchmarks/musr \
  --timeout 1800 \
  --output sweep_results.csv \
  dataset.n=75 cachier.enable_caching=false
```

Extra args after the options (`dataset.n=75`, etc.) are base overrides
applied to every config.

### 3. View results

```bash
uv run -m secretagent.cli.optimize summary sweep_results.csv
```

Or load in Python:

```python
import pandas as pd
df = pd.read_csv('sweep_results.csv')
print(df.sort_values('accuracy', ascending=False))
```

## Programmatic Usage

```python
from secretagent.optimize import ConfigSpace, GridSearchRunner

space = ConfigSpace(variants={
    'llm.thinking': [True, False],
    'ptools.answer_question.method': ['simulate', 'direct'],
})

runner = GridSearchRunner(
    command='uv run python expt.py run --config-file conf/murder.yaml',
    space=space,
    base_dotlist=['dataset.n=75', 'cachier.enable_caching=false'],
    cwd='benchmarks/musr',
    timeout=1800,
    metric='correct',
)

summary = runner.run_all()
print(summary)
runner.save_summary('results.csv')
```

## CLI Reference

### `sweep`

Run a grid search over a config space.

```
uv run -m secretagent.cli.optimize sweep [OPTIONS] [DOTLIST_OVERRIDES...]
```

| Option | Default | Description |
|---|---|---|
| `--command` | (required) | Base command to run (quoted string) |
| `--space-file` | (required) | YAML file defining search space |
| `--prefix` | `sweep` | Experiment name prefix |
| `--cwd` | current dir | Working directory for subprocesses |
| `--timeout` | `1800` | Timeout per config in seconds |
| `--metric` | `correct` | Metric column to optimize |
| `--output` | `sweep_summary.csv` | Output summary CSV path |

Extra positional args are treated as base dotlist overrides applied to
all configs.

### `summary`

Display results from a saved sweep.

```
uv run -m secretagent.cli.optimize summary SWEEP_RESULTS.csv [--top-n N]
```

| Option | Default | Description |
|---|---|---|
| `--top-n` | `10` | Number of top results to show |

## Search Space Format

The YAML file can use either format:

```yaml
# Standard format with variants key
variants:
  key1:
    - value1
    - value2
  key2:
    - value3
    - value4
```

```yaml
# Also valid: top-level keys (without variants wrapper)
key1:
  - value1
  - value2
key2:
  - value3
  - value4
```

All values must be lists. The optimizer generates every combination
(Cartesian product). A space with 3 keys of sizes 2, 3, 2 produces
2 × 3 × 2 = 12 configs.

## Output Format

The sweep produces:

1. **Per-config result directories** — standard format under
   `evaluate.result_dir`, each with `results.csv`, `results.jsonl`,
   and `config.yaml`. Named `{prefix}_{idx:03d}`.

2. **Summary CSV** — one row per config with columns:

| Column | Description |
|---|---|
| `config_idx` | Config index (0-based) |
| `expt_name` | Experiment name (e.g., `sweep_000`) |
| *search dimensions* | One column per search space key |
| `accuracy` | Mean of the `metric` column |
| `elapsed` | Wall clock time in seconds |
| `total_cost` | Sum of per-example costs |
| `cost_per_q` | Mean cost per example |
| `total_latency` | Sum of per-example latencies |
| `latency_per_q` | Mean latency per example |
| `input_tokens_per_q` | Mean input tokens per example |
| `output_tokens_per_q` | Mean output tokens per example |
| `status` | `ok`, `failed`, or `timeout` |

The summary is compatible with pandas and can be loaded directly for
analysis.

## Compatibility

The optimizer works with any benchmark that follows the secretagent
experiment pattern:

1. Uses typer CLI with `allow_extra_args` for dotlist overrides
2. Calls `Evaluator.evaluate()` which prints
   `Accuracy: X% (N/M)` and `saved in <path>`

All existing benchmarks (MUSR, NaturalPlan, sports_understanding,
MedCalc, RuleArena) satisfy these requirements.

## Example: MUSR Murder Sweep

```yaml
# benchmarks/musr/sweep_murder.yaml
variants:
  evaluate.entry_point:
    - answer_question
    - answer_question_workflow
  llm.thinking:
    - "true"
    - "false"
```

```bash
cd benchmarks/musr
uv run -m secretagent.cli.optimize sweep \
  --command "uv run python expt.py run --config-file conf/murder.yaml" \
  --space-file sweep_murder.yaml \
  --cwd . \
  dataset.n=75 llm.model=together_ai/deepseek-ai/DeepSeek-V3
```

Sample output:

```
SWEEP RESULTS (sorted by accuracy)
============================================================
 expt_name     evaluate.entry_point llm.thinking  accuracy  cost_per_q  latency_per_q
 sweep_001          answer_question        false    0.6400      0.0021           1.8
 sweep_003 answer_question_workflow        false    0.6267      0.0079          20.5
 sweep_000          answer_question         true    0.6133      0.0025           8.1
 sweep_002 answer_question_workflow         true       NaN         NaN           NaN  (timeout)

Best: sweep_001 — 64.0%
  evaluate.entry_point = answer_question
  llm.thinking = false
```

## Module Structure

```
src/secretagent/
    optimize/
        __init__.py          # re-exports ConfigSpace, GridSearchRunner
        config_space.py      # ConfigSpace (Pydantic model)
        grid_search.py       # GridSearchRunner
    cli/
        optimize.py          # CLI (sweep, summary)
```
