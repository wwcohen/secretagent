# Orchestration Learner

Supervisor-driven pipeline hill climbing. A powerful reasoning LLM (the
"supervisor") iteratively analyzes failures in a pipeline, proposes
targeted code changes, and evaluates them. Improvements are kept;
regressions are rolled back. The system tracks train/eval accuracy
curves, per-iteration artifacts, and supervisor costs.

## Structure

### What it does

The Orchestration Learner takes a working pipeline (defined as a
`ptools_evolved.py` module with `@interface`-decorated functions) and
improves it through a loop:

1. Evaluate the pipeline on a training set
2. Profile per-ptool cost, accuracy, and error patterns
3. Show the supervisor LLM the full source, profiling, failure traces,
   and iteration history
4. The supervisor proposes a modified `ptools_evolved.py`
5. Evaluate the new version -- keep if better, rollback if worse
6. Repeat

### Key files

| File | Role |
|------|------|
| `cli/orchestration_learner.py` | CLI entry point (`run` and `view` commands) |
| `orchestrate/improve.py` | Core improvement loop (`improve_with_supervisor`) and data models (`IterationRecord`, `SupervisorReport`) |
| `orchestrate/composer.py` | `recompose()` -- builds the supervisor prompt and parses the LLM response |
| `orchestrate/prompt_templates/recompose.txt` | Supervisor prompt template (strategy guidance, output format) |
| `orchestrate/profiler.py` | `profile_from_results()` -- reads `results.jsonl` to compute per-ptool metrics |
| `orchestrate/catalog.py` | `PtoolCatalog` -- collects interface signatures/docstrings for prompts |
| `orchestrate/transforms/base.py` | `format_profiling_summary()` -- renders profiling data as text |

## Usage

Run from a benchmark directory (e.g. `benchmarks/medcalc/`).

### Basic run

```bash
uv run python -m secretagent.cli.orchestration_learner run \
    --config-file conf/workflow.yaml \
    --n-train 110 --n-eval 110 \
    --max-iterations 10
```

### Common flags

| Flag | Default | Description |
|------|---------|-------------|
| `--config-file` | (required) | Starting config YAML |
| `--n-train` | 110 | Training set size |
| `--n-eval` | 110 | Held-out eval set size |
| `--max-iterations` | 10 | Max improvement iterations |
| `--target-accuracy` | None | Stop early when reached |
| `--supervisor-model` | `gemini/gemini-3.1-pro-preview` | Supervisor LLM model |
| `--custom-instructions` | `''` | Extra text or `@filepath` for supervisor prompt |
| `--model-change` | `''` | JSON file with model choices for supervisor |
| `--train-split` | `train` | HuggingFace split for training data |
| `--eval-split` | `test` | HuggingFace split for eval data |
| `--debug` | False | Echo supervisor I/O (sets `echo.orchestrate_llm=True`) |
| `--resume` | `''` | Path to a previous `.orch_learner` directory to continue from |

Extra positional arguments are passed as dotlist config overrides.

### Resume a previous run

```bash
uv run python -m secretagent.cli.orchestration_learner run \
    --config-file conf/workflow.yaml \
    --n-train 110 --n-eval 110 \
    --max-iterations 10 \
    --resume results/orchestration_learner/20260419.215731.orch_learner
```

This loads the best `ptools_evolved.py` and iteration history from the
previous run and continues the improvement loop from where it left off.

### Generate HTML report

```bash
uv run python -m secretagent.cli.orchestration_learner view \
    results/orchestration_learner/20260419.215731.orch_learner
```

Reads `report.json` and regenerates `report.html` without re-running
anything.

### Reusing a learned pipeline at eval time

Each run now emits `implementation.yaml` under its output directory with
the shape:

```yaml
calculate_medical_value:
  method: direct
  fn: __learned__.workflow    # actual fn name, derived from ptools.<entry>.fn
  learner: orch_learner
```

The `direct` factory resolves `fn: __learned__.<attr>` by globbing
`{learn.train_dir}/*.orch_learner/ptools_evolved.py` and binding the
attribute. It also binds the evolved module's sub-Interfaces from the
current `ptools` config so the learned entry-point can call its
co-module tools.

To eval a learned pipeline, override the binding like so:

```
ptools.calculate_medical_value.method=direct \
ptools.calculate_medical_value.fn=__learned__.workflow \
ptools.calculate_medical_value.learner=orch_learner \
learn.train_dir=results/orchestration_learner
```

## How It Works

### The improvement loop (step by step)

Each iteration in `improve_with_supervisor()` does:

1. **Profile** -- `format_profiling_summary()` renders per-ptool metrics
   (cost fraction, calls/case, errors) from the last evaluation run.
   Also reports which ptools are actually called and the current
   train-eval gap if eval data exists.

2. **Format failure traces** -- `_format_failure_traces()` reads
   `results.jsonl`, groups failures by category, and selects a diverse
   sample. Each failure includes the real input data (from the dataset),
   the full LLM call trace (rollout), and predicted vs expected output.

3. **Build iteration history** -- `_format_iteration_history()` shows
   every past iteration: accuracy, kept/rolled-back, and full reasoning.
   Rolled-back iterations are flagged so the supervisor avoids repeating
   failed approaches.

4. **Call supervisor** -- `recompose()` in `composer.py` fills the
   `recompose.txt` template with the full `ptools_evolved.py` source,
   profiling, failures, history, and optional custom instructions. The
   supervisor runs with `reasoning_effort=high` and a 600-second timeout.

5. **Parse response** -- The supervisor's output is parsed for three
   sections: `<ptools_file>` (the complete modified file),
   `<reasoning>` (what was changed and why), and optional `<config>`
   (dotlist overrides like model switches).

6. **Validate** -- The new source is checked with `ast.parse()`. Syntax
   errors cause an immediate rollback.

7. **Reload and evaluate** -- The new source is written to
   `ptools_evolved.py`, the module is re-executed via
   `spec.loader.exec_module()` (not `importlib.reload()`), interfaces
   are re-bound, and the train set is re-evaluated.

8. **Keep or rollback** -- See below.

### Keep/rollback logic

The decision follows strict rules:

- **Train regression** (`new < best`): Rolled back immediately. Eval is
  skipped entirely (saves an expensive eval run).
- **Train improvement** (`new > best`): Kept unconditionally. Eval is
  still run for tracking but does not affect the decision.
- **Train tie** (`new == best`): Eval is used as tiebreaker. Kept only
  if `eval_acc > best_eval_acc`.
- **No change proposed**: Skipped. After 5 consecutive no-change or
  no-improvement iterations, the loop stops early.

### Batch watchdog for API hang protection

The evaluator (in `evaluate.py`) uses `signal.alarm` as a hard watchdog
when running with `evaluate.max_workers > 1`. Each batch of cases gets
a generous timeout (`case_timeout * batch_size / max_workers + 60s`).
If a batch hangs (e.g. an API socket stalls at the C level),
`SIGALRM` interrupts it. Timed-out cases are retried individually with
a per-case alarm, and truly stuck cases are recorded with
`_timeout=True`.

### All LLM calls go through @interface

Every LLM call in the pipeline is made through `@interface`-decorated
functions bound via the config. This means the profiler and recorder
see every call, and the supervisor prompt includes full per-ptool
breakdowns of cost, latency, and error rates.

## Output Structure

A run creates a timestamped directory under `results/orchestration_learner/`:

```
results/orchestration_learner/
  20260419.215731.orch_learner/
    config.yaml             # Effective config snapshot for this learner run
    run_metadata.json       # Benchmark/config provenance for the learner run
    report.json              # Full structured report (SupervisorReport model)
    report.html              # Self-contained interactive HTML report
    ptools_evolved.py        # Best version of the evolved ptools file
    implementation.yaml      # Eval-time binding: `direct` + __learned__.<fn> + learner:orch_learner
    prompt_templates/        # Copied from benchmark so the run is self-contained
    plots/                   # Matplotlib plots (if available)
      accuracy_over_iterations.png
      cost_over_iterations.png
      accuracy_vs_cost.png
    final_eval/              # Final evaluation on held-out set
      results.csv
      results.jsonl
    iterations/
      iter_000_baseline/
        config.yaml         # Config snapshot for the baseline iteration
        result_dirs.json    # Train/eval result directory pointers
        ptools_evolved.py    # Snapshot of baseline code
      iter_001/
        config_before.yaml  # Config before applying any proposed overrides
        config_after.yaml   # Config after applying proposed overrides (if any)
        result_dirs.json    # Train/eval result directory pointers
        ptools_before.py     # Code before this iteration's changes
        ptools_after.py      # Code after supervisor's changes
        reasoning.txt        # Supervisor's reasoning
        profiling_summary.txt
        failure_traces.txt
        iteration_history.txt
        supervisor_prompt.txt    # Full prompt sent to supervisor
        supervisor_response.txt  # Full raw supervisor response
        config_overrides.txt     # Config changes (if any)
        outcome.txt              # KEPT or ROLLED BACK with accuracy delta
      iter_002/
        ...
```

The `report.json` is saved after every iteration, so progress survives
interruption.

### report.json schema

Top-level fields (`SupervisorReport`):

| Field | Type | Description |
|-------|------|-------------|
| `iterations` | list | List of `IterationRecord` objects |
| `best_iteration` | int | Iteration number with best train accuracy |
| `best_train_accuracy` | float | Best train accuracy achieved |
| `final_eval_accuracy` | float or null | Accuracy on held-out eval set (run at the end) |
| `total_supervisor_cost` | float | Cumulative $ spent on supervisor LLM calls |
| `best_code` | str | Reference to ptools_evolved.py |
| `best_config_overrides` | list[str] | Config overrides from the best iteration |
| `config_snapshot_path` | str or null | Relative path to the saved config snapshot |

Per-iteration fields (`IterationRecord`):

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | int | 0 = baseline, 1+ = improvement iterations |
| `train_accuracy` | float | Accuracy on training set |
| `train_cost` | float | Average cost per case |
| `train_failures` | int | Number of incorrect cases |
| `train_timeouts` | int | Number of timed-out cases |
| `eval_accuracy` | float or null | Accuracy on eval set (null if skipped) |
| `eval_cost` | float or null | Average eval cost per case |
| `supervisor_cost` | float | Cost of the supervisor LLM call for this iteration |
| `reasoning` | str | Supervisor's reasoning for the change |
| `kept` | bool | Whether this iteration's changes were kept |
| `config_overrides` | list[str] | Dotlist config overrides proposed |
| `train_result_dir` | str or null | Result directory for the training evaluation |
| `eval_result_dir` | str or null | Result directory for the eval evaluation |
| `config_before_path` | str or null | Relative path to the pre-override config snapshot |
| `config_after_path` | str or null | Relative path to the post-override config snapshot |

## Configuration

### Key config knobs

Set these in the workflow YAML or as dotlist overrides:

| Key | Default | Description |
|-----|---------|-------------|
| `evaluate.max_workers` | 1 | Parallel evaluation threads (set >1 for speed) |
| `evaluate.case_timeout` | 300 | Per-case timeout in seconds (for batch watchdog) |
| `evaluate.record_details` | False | Set True to capture full rollouts in results.jsonl (the learner sets this automatically) |
| `llm.model` | (from config) | Model used by the pipeline's `@interface` functions |
| `llm.max_tokens` | (from config) | Max output tokens for pipeline LLM calls |
| `llm.timeout` | (from config) | Timeout for pipeline LLM calls |
| `cachier.enable_caching` | True | LLM call caching (enabled by default in the learner) |
| `cachier.cache_dir` | `llm_cache` | Directory for cached LLM responses |

### Supervisor model

The supervisor LLM is configured via `--supervisor-model` (default:
`gemini/gemini-3.1-pro-preview`). During the supervisor call,
`reasoning_effort` is forced to `high` and timeout is set to 600
seconds, regardless of the pipeline's LLM config.

### Example workflow config

```yaml
# conf/workflow.yaml
llm:
  model: together_ai/deepseek-ai/DeepSeek-V3.1
  max_tokens: 65536

cachier:
  cache_dir: llm_cache
  enable_caching: true

evaluate:
  result_dir: results
  expt_name: workflow
  entry_point: calculate_medical_value

ptools:
  identify_calculator:
    method: simulate
  extract_clinical_values:
    method: simulate
  compute_calculation:
    method: direct
    fn: ptools.compute_calculation_impl
  calculate_medical_value:
    method: direct
    fn: ptools.workflow
```

## Results Format

### Iteration log table

The CLI prints a summary table at the end of a run:

```
Iteration log:
  Iter     Train  Fail   TO      Eval    Sup $      Status
     0    80.0%    22    0    73.6%  $0.0000    BASELINE
     1    80.0%    22    0    73.6%  $0.1217    ROLLBACK
     2    78.2%    24    0    70.9%  $0.1016    ROLLBACK
     3    80.0%    22    0    73.6%  $0.1556      KEPT
```

- **Train**: accuracy on the training set
- **Fail**: number of incorrect cases
- **TO**: number of timed-out cases
- **Eval**: accuracy on held-out eval set (shown only when eval is run)
- **Sup $**: cost of the supervisor LLM call for that iteration
- **Status**: BASELINE (iter 0), KEPT, or ROLLBACK

### HTML report

The `report.html` is a self-contained interactive page with:

- Summary cards (best train accuracy, final eval accuracy, iteration
  count, total supervisor cost)
- Accuracy curve chart (train in blue, eval in orange, kept points in
  green, rollbacks in red)
- Iteration log table matching the CLI output
- Expandable iteration details with:
  - Supervisor reasoning
  - Code diff (color-coded additions/deletions)
  - Profiling summary
  - Failure traces
  - Full supervisor prompt and response
  - Outcome summary

Open it directly in a browser -- no server needed.
