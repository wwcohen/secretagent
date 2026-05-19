# Ptool Orchestrator

The orchestrator automatically generates pipeline functions from a set of
implemented ptools and a task description. Instead of hand-coding workflow
functions, you describe what the pipeline should accomplish and the
orchestrator uses a powerful LLM to compose the available ptools into a
coherent sequence.

## Architecture

```
                     ┌──────────────────────────┐
                     │  User provides:          │
                     │  - task description       │
                     │  - module with ptools     │
                     │  - (optional) test case   │
                     └─────────┬────────────────┘
                               │
                     ┌─────────▼────────────────┐
                     │  PtoolCatalog             │
                     │  Collects ptool           │
                     │  signatures + docstrings  │
                     └─────────┬────────────────┘
                               │
                     ┌─────────▼────────────────┐
                     │  compose()                │
                     │  Single LLM call          │
                     │  (Qwen 397B via Together) │
                     └─────────┬────────────────┘
                               │
                     ┌─────────▼────────────────┐
                     │  ruff --fix               │
                     │  Deterministic cleanup    │
                     └─────────┬────────────────┘
                               │
                     ┌─────────▼────────────────┐
                     │  Pipeline                 │
                     │  exec() into callable     │
                     │  with ptools in namespace │
                     └─────────┬────────────────┘
                               │
                     ┌─────────▼────────────────┐
                     │  Smoke test (optional)    │
                     │  Retry up to max_retries  │
                     │  with error feedback      │
                     └─────────┬────────────────┘
                               │
                     ┌─────────▼────────────────┐
                     │  Result: callable bound   │
                     │  to Interface via         │
                     │  OrchestrateFactory       │
                     └──────────────────────────┘
```

The key design principle: the generated pipeline calls `Interface` objects
(not raw functions), so the entire existing infrastructure — recording,
cost tracking, caching, implementation swapping — works automatically.

## Quickstart

### Programmatic usage

```python
from secretagent.core import interface
from secretagent import config
from secretagent.orchestrate import PtoolCatalog, compose, build_pipeline
from secretagent.orchestrate.pipeline import _entry_signature_from_interface

# 1. Define and implement ptools
@interface
def double(x: int) -> int:
    """Double the input value."""
    return x * 2

@interface
def add_one(x: int) -> int:
    """Add one to the input."""
    return x + 1

double.implement_via('direct')
add_one.implement_via('direct')

# 2. Define the workflow interface (unimplemented)
@interface
def my_workflow(x: int) -> int:
    """Double x, then add one."""
    ...

# 3. Configure and compose
config.configure(orchestrate={'model': 'together_ai/Qwen/Qwen3.5-397B-A17B'})

catalog = PtoolCatalog.from_interfaces([double, add_one])
entry_sig = _entry_signature_from_interface(my_workflow)
code = compose('Double x, then add one.', catalog, entry_sig)

# 4. Build and execute
pipeline = build_pipeline(code, my_workflow, [double, add_one])
print(pipeline(5))   # → 11
print(pipeline.source)  # print generated code
```

### Config-driven usage (recommended for benchmarks)

```yaml
# conf/my_experiment.yaml
llm:
  model: together_ai/Qwen/Qwen3.5-9B

orchestrate:
  model: together_ai/Qwen/Qwen3.5-397B-A17B
  max_retries: 3

ptools:
  extract_data:
    method: simulate
  analyze_data:
    method: simulate
  format_answer:
    method: simulate
  # Listed LAST so the above ptools are already implemented
  solve_problem:
    method: orchestrate
    task_description: "Extract data, analyze it, then format the answer."
```

```python
from secretagent.core import implement_via_config
import my_ptools  # module with @interface definitions

config.configure(yaml_file='conf/my_experiment.yaml')
implement_via_config(my_ptools, config.require('ptools'))

# solve_problem is now auto-composed from the other ptools
result = my_ptools.solve_problem(input_data)
```

**Important ordering rule:** The orchestrated interface must be listed
last in the `ptools:` config section. The orchestrator builds its catalog
from currently-implemented interfaces, so other ptools must be implemented
first.

## API Reference

### `PtoolCatalog`

**Module:** `secretagent.orchestrate.catalog`

Collects ptool metadata into a prompt-ready format.

```python
class PtoolCatalog:
    ptools: list[PtoolInfo]
```

#### `PtoolCatalog.from_interfaces(interfaces, exclude=None, include_unimplemented=False)`

Build a catalog from a list of `Interface` objects.

- **interfaces** (`list[Interface]`): interfaces to include
- **exclude** (`list[str] | None`): names to exclude (e.g., the workflow itself)
- **include_unimplemented** (`bool`): if `False` (default), skip interfaces
  without an implementation

```python
catalog = PtoolCatalog.from_interfaces(
    all_interfaces(),
    exclude=['my_workflow'],
)
```

#### `PtoolCatalog.from_module(module, exclude=None, include_unimplemented=False)`

Build a catalog from all `Interface` objects defined in a Python module.

```python
import my_ptools
catalog = PtoolCatalog.from_module(my_ptools, exclude=['my_workflow'])
```

#### `PtoolCatalog.render() -> str`

Render all ptool stubs as text for the LLM prompt. Returns the raw
source code (signature + docstring) for each ptool, separated by blank
lines.

#### `PtoolCatalog.names -> list[str]`

List of ptool names in the catalog.

---

### `PtoolInfo`

**Module:** `secretagent.orchestrate.catalog`

Lightweight dataclass holding metadata about a single ptool.

```python
@dataclass
class PtoolInfo:
    name: str
    doc: str
    src: str
    param_names: list[str]
    param_types: dict[str, str]
    return_type: str

    # Future V2+ fields (None in V1)
    avg_cost: float | None = None
    avg_latency: float | None = None
    success_rate: float | None = None
    unused_success_rate: float | None = None
    lift: float | None = None
```

The metric fields (`avg_cost`, `avg_latency`, `success_rate`,
`unused_success_rate`, `lift`) are placeholders for the future optimizer.
They are not populated in V1.

---

### `compose(task_description, catalog, entry_signature, model=None) -> str`

**Module:** `secretagent.orchestrate.composer`

Generate a pipeline function body by prompting an LLM.

- **task_description** (`str`): what the pipeline should accomplish
- **catalog** (`PtoolCatalog`): available ptools
- **entry_signature** (`str`): the function signature line, e.g.
  `"def my_workflow(x: str, y: int) -> str:"`
- **model** (`str | None`): LLM model; defaults to
  `config.require('orchestrate.model')`

Returns the generated Python code as a string (the function body, not
including the `def` line).

The function:
1. Loads the `compose.txt` prompt template
2. Substitutes template variables (tool stubs, task description, etc.)
3. Calls the LLM via `llm_util.llm()` (gets cachier caching for free)
4. Extracts Python from `` ```python `` blocks
5. Strips any leading `def` line the LLM may have included
6. Runs `ruff check --fix` for deterministic cleanup

---

### `compose_with_retry(task_description, catalog, entry_signature, test_fn, model=None, max_retries=None) -> tuple[str, int]`

**Module:** `secretagent.orchestrate.composer`

Like `compose()`, but with smoke-test validation and automatic retry.

- **test_fn** (`Callable[[str], None]`): takes the generated code string
  and should raise on failure (e.g., build a Pipeline and run it on a
  test case)
- **max_retries** (`int | None`): max attempts; defaults to
  `config.get('orchestrate.max_retries', 3)`

Returns `(code, attempt)` where `attempt` is 1-indexed (for pass@k
reporting).

On each failure:
- Catches the exception
- Appends the error message to the prompt
- Retries with informed correction

If all retries fail, raises `RuntimeError` with all attempted codes and
error messages.

---

### `Pipeline`

**Module:** `secretagent.orchestrate.pipeline`

Wraps generated code into a callable with ptools in its exec namespace.

```python
pipeline = Pipeline(code, entry_signature, namespace)
result = pipeline(*args, **kwargs)
print(pipeline.source)  # full reconstructable source
```

- **code** (`str`): the function body
- **entry_signature** (`str`): the `def` line
- **namespace** (`dict[str, Any]`): names available to the code (ptools, etc.)

The `Pipeline.source` property returns the full source code (def + body),
useful for debugging and future pipeline bank storage.

---

### `build_pipeline(code, entry_interface, tool_interfaces) -> Pipeline`

**Module:** `secretagent.orchestrate.pipeline`

Convenience function that builds a Pipeline from Interface objects.

- **code** (`str`): generated function body
- **entry_interface** (`Interface`): the workflow Interface this pipeline
  implements
- **tool_interfaces** (`list[Interface]`): interfaces available in the
  code's namespace

The namespace maps ptool names → Interface objects, so calling a ptool in
the generated code dispatches through `Interface.__call__`, which means
recording, cost tracking, and implementation swapping all work
transparently.

---

### `OrchestrateFactory`

**Module:** `secretagent.orchestrate`

An `Implementation.Factory` that generates pipeline implementations
using the orchestrator.

Registered as `'orchestrate'` in the factory registry.

#### `setup(task_description=None, exclude=None, test_case=None, **kw)`

- **task_description** (`str | None`): defaults to the interface's docstring
- **exclude** (`list[str] | None`): additional names to exclude from catalog
- **test_case** (`dict | list | None`): if provided, enables retry logic.
  Should be `{'input_args': [arg1, arg2, ...]}` or just `[arg1, arg2]`.

When `test_case` is provided, uses `compose_with_retry()` internally.

## Configuration

All config keys follow the existing secretagent config system
(`config.configure()`, `config.get()`, YAML files).

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `orchestrate.model` | `str` | — (required) | LLM model for pipeline composition |
| `orchestrate.max_retries` | `int` | `3` | Max retry attempts for `compose_with_retry` |
| `echo.orchestrate` | `bool` | `False` | Print generated pipeline code and attempt info |
| `echo.orchestrate_llm` | `bool` | `False` | Print raw LLM output from the orchestrator |

Example YAML:

```yaml
orchestrate:
  model: together_ai/Qwen/Qwen3.5-397B-A17B
  max_retries: 5

echo:
  orchestrate: true
```

## Error Handling

### Common errors

**`ValueError: No implemented ptools available for orchestration`**
The orchestrator found no implemented interfaces to compose. Ensure other
ptools are implemented before the orchestrated one in your config.

**`ValueError: No ```python``` code block found`**
The LLM response didn't contain a Python code block. Usually means the
model misunderstood the prompt. Try a different orchestrator model.

**`SyntaxError` during Pipeline compilation**
The LLM generated invalid Python. With `compose_with_retry()`, this is
automatically caught and retried with the error message.

**`RuntimeError: Pipeline generation failed after N attempts`**
All retry attempts failed. The error includes all attempted codes and
their error messages for debugging.

### How retries work

1. `compose()` generates initial code
2. `test_fn(code)` runs a smoke test (build Pipeline, call with test input)
3. If it raises, the error is appended to the prompt
4. The LLM sees both the failed code and the error message
5. Repeat up to `max_retries` times

Each retry is *informed* — the LLM gets the specific error, which
dramatically improves success rates compared to blind retry.

## How It Works Internally

### The prompt template

`orchestrate/prompt_templates/compose.txt` uses `string.Template` with
these variables:

- `$tool_stubs`: rendered ptool source code (signatures + docstrings)
- `$tool_names`: comma-separated list of available tool names
- `$task_description`: what the pipeline should accomplish
- `$entry_signature`: the function signature the code will be wrapped in

### Code extraction

The LLM response is scanned for `` ```python ... ``` `` blocks. If
multiple blocks exist, the last one is used (handles draft → refined
patterns).

### Ruff cleanup

After extraction, the code is wrapped in the function signature, written
to a temp file, and `ruff check --fix --quiet` is run on it. This
catches formatting issues, unused imports, and simple mistakes. If ruff
isn't available, the code passes through unchanged.

### Compilation

`Pipeline._compile()` uses `exec()` to compile the generated function
in a namespace containing the ptool Interface objects. This is the same
trust model as `PoTFactory`'s `LocalPythonExecutor`.

## Integration with Benchmarks

To add orchestration to an existing benchmark:

1. Create a new config file (e.g., `conf/murder_orchestrated.yaml`)
2. List all tool ptools with their implementation methods
3. Add the workflow interface last with `method: orchestrate`
4. Run the experiment as usual

```yaml
# benchmarks/musr/conf/murder_orchestrated.yaml
llm:
  model: together_ai/Qwen/Qwen3.5-9B

orchestrate:
  model: together_ai/Qwen/Qwen3.5-397B-A17B

cachier:
  cache_dir: llm_cache

evaluate:
  expt_name: murder_orchestrated
  result_dir: results
  entry_point: answer_question_workflow

dataset:
  split: murder_mysteries
  shuffle_seed: 42
  n: 20

ptools:
  raw_answer:
    method: simulate
  extract_suspects_and_evidence:
    method: simulate
  verify_alibis:
    method: simulate
  deduce_murderer:
    method: simulate
  extract_index:
    method: simulate
  answer_question_workflow:
    method: orchestrate
    task_description: >
      Solve murder mystery by extracting suspects and evidence,
      verifying alibis, deducing the murderer, then matching
      to the answer choices and returning the 0-based index.
```

Run:
```bash
uv run python benchmarks/musr/expt.py run --config-file conf/murder_orchestrated.yaml
```

## Module Structure

```
src/secretagent/orchestrate/
    __init__.py              # OrchestrateFactory, public exports
    catalog.py               # PtoolCatalog, PtoolInfo
    composer.py              # compose(), compose_with_retry()
    pipeline.py              # Pipeline, build_pipeline()
    prompt_templates/
        compose.txt          # LLM prompt template
```
