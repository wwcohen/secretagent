# secretagent

Lightweight Python framework for building agentic systems where
everything looks like code.

You define Python stubs with only a type signature and docstring,
decorate them with `@interface`, and separately bind them to concrete
implementations, which can be Python code, single calls to an LLM, or
agentic, tool-using calls to an LLM.  

There is also support for implementing an Interface using only an LLM
and the docstring and type signature associated with the stub.

This architecture lets you easily explore the space of different ways
to decompose a problem into modular components.

## Installation

```bash
uv sync
```

## Quickstart

Define a function stub and bind it to an LLM-based implementation:

```python
from secretagent.core import implement_via

@implement_via('simulate', llm={'model': 'claude-haiku-4-5-20251001'})
def translate(english_sentence: str) -> str:
    """Translate a sentence in English to French."""

print(translate("What's for lunch today?"))
# Qu'est-ce qu'il y a pour le dejeuner aujourd'hui?
```

You can also get structured Pydantic output:

```python
from pydantic import BaseModel
from secretagent.core import implement_via
import secretagent.implement.pydantic  # registers simulate_pydantic factory

class FrenchEnglishTranslation(BaseModel):
    english_text: str
    french_text: str

@implement_via('simulate_pydantic', llm={'model': 'claude-haiku-4-5-20251001'})
def translate_structured(english_sentence: str) -> FrenchEnglishTranslation:
    """Translate a sentence in English to French."""

print(translate_structured("What's for lunch today?"))
```

Run the full quickstart example:

```bash
uv run examples/quickstart.py
```

## Configuration

Configuration is managed via `secretagent.config` using OmegaConf:

```python
from secretagent import config

# load from a YAML file
config.configure(yaml_file='conf.yaml')

# or set values directly
config.configure(llm={'model': 'claude-haiku-4-5-20251001'})

# temporary overrides via context manager
with config.configuration(cachier={'enable_caching': False}):
    result = my_function()
```

Key configuration sections:

- `llm.model` -- LLM model name passed to litellm
- `echo.*` -- control debug output (llm_input, llm_output, model, service, call)
- `cachier.*` -- caching options (enable_caching, cache_dir, etc.)
- `evaluate.*` -- experiment settings (expt_name, result_dir)

## Core API

- `@interface` -- decorator that turns a stub function into an Interface
- `@implement_via(method, **kw)` -- create an Interface and bind it in one step
- `interface.implement_via(method, **kw)` -- bind an existing Interface

### Built-in factories

- **`'direct'`** -- use the function body (or another callable) as the implementation.
  ```python
  my_iface.implement_via('direct')                    # use the stub's own body
  my_iface.implement_via('direct', fn=some_function)  # use a specific callable
  my_iface.implement_via('direct', fn='mymod.func')   # resolve a dotted name
  ```

- **`'simulate'`** -- prompt an LLM to predict the function output from the
  stub's docstring and type signature.
  ```python
  my_iface.implement_via('simulate', llm={'model': 'claude-haiku-4-5-20251001'})
  ```

- **`'simulate_pydantic'`** -- like simulate but uses a pydantic-ai Agent,
  which can call tools in a ReAct-like loop and return structured Pydantic output.
  ```python
  my_iface.implement_via('simulate_pydantic', llm={'model': 'claude-haiku-4-5-20251001'})
  my_iface.implement_via('simulate_pydantic', tools='__all__')   # use all other interfaces as tools
  my_iface.implement_via('simulate_pydantic', tools=[tool_a, tool_b])  # specific tools
  ```

- **`'program_of_thought'`** -- generate Python code with an LLM and execute it
  in a sandboxed executor. Tools are available as callable functions in the
  generated code.
  ```python
  my_iface.implement_via('program_of_thought', llm={'model': 'claude-haiku-4-5-20251001'})
  my_iface.implement_via('program_of_thought', tools='__all__')  # default: all other interfaces
  my_iface.implement_via('program_of_thought', tools=[tool_a])   # specific tools
  ```

- **`'prompt_llm'`** -- use a custom prompt template with the LLM.
  ```python
  my_iface.implement_via('prompt_llm',
      prompt_template_str='Translate to French: $text',
      llm={'model': 'claude-haiku-4-5-20251001'})
  my_iface.implement_via('prompt_llm',
      prompt_template_file='prompts/my_template.txt',
      answer_pattern=r'<answer>(.*)</answer>')
  ```

All factories also accept config overrides as keyword arguments (e.g.
`llm={'model': ...}`, `echo={'llm_input': True}`), which are applied
via `config.configuration()` during execution.


## Benchmarks

Benchmarks live in `benchmarks/`. Each benchmark has its own `expt.py`
runner, YAML configs in `conf/`, and ptools (decomposed sub-tasks) in
`ptools.py`.

### Universal benchmark runner

The `bench` CLI dispatches to per-benchmark runners as subprocesses:

```bash
# list all registered benchmarks with eval pool and minibatch sizes
uv run -m secretagent.cli.bench list

# run a single benchmark (uses default simulate strategy)
uv run -m secretagent.cli.bench run sports_understanding --minibatch

# run with a specific model
uv run -m secretagent.cli.bench run medcalc --minibatch llm.model=gemini/gemini-3.1-flash-lite-preview

# run all benchmarks
uv run -m secretagent.cli.bench run-all --minibatch
```

### Running a benchmark directly

Each benchmark can also be run directly with full config control:

```bash
cd benchmarks/bbh/sports_understanding

# simulate strategy (zero-shot LLM)
uv run python -m secretagent.cli.expt run \
    --interface ptools.are_sports_in_sentence_consistent \
    ptools.are_sports_in_sentence_consistent.method=simulate \
    llm.model=gemini/gemini-3.1-flash-lite-preview dataset.n=20

# workflow strategy (multi-step pipeline)
uv run python -m secretagent.cli.expt run \
    --interface ptools.are_sports_in_sentence_consistent \
    ptools.are_sports_in_sentence_consistent.method=direct \
    ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow \
    llm.model=gemini/gemini-3.1-flash-lite-preview dataset.n=20
```

For benchmarks with their own `expt.py` (medcalc, musr, etc.):

```bash
cd benchmarks/medcalc

# simulate
uv run python expt.py run --config-file conf/simulate.yaml \
    llm.model=gemini/gemini-3.1-flash-lite-preview dataset.n=110

# workflow (multi-stage extraction + Python computation)
uv run python expt.py run --config-file conf/workflow.yaml \
    llm.model=gemini/gemini-3.1-flash-lite-preview dataset.n=110

# program of thought (LLM generates code)
uv run python expt.py run --config-file conf/pot.yaml \
    llm.model=gemini/gemini-3.1-flash-lite-preview dataset.n=110
```

### Strategies

Each benchmark supports multiple implementation strategies for the
top-level interface:

| Strategy | Method | What it does |
|----------|--------|-------------|
| **simulate** | `method=simulate` | One LLM call predicts the answer from the function docstring |
| **unstructured** | `method=direct`, `fn=zeroshot_unstructured_workflow` | One LLM call with custom prompt + output formatting |
| **workflow** | `method=direct`, `fn=<benchmark>_workflow` | Hand-coded multi-step pipeline calling simulated sub-ptools |
| **POT** | `method=program_of_thought` | LLM generates Python code which is then executed |

### Viewing results

```bash
# list experiments
uv run -m secretagent.cli.results list benchmarks/bbh/sports_understanding/results/*/

# compare accuracy across strategies
uv run -m secretagent.cli.results average --metric correct --metric cost- \
    benchmarks/bbh/sports_understanding/results/*/

# plot accuracy vs cost
uv run -m secretagent.cli.results plot --metric correct --metric cost- \
    --output plot.png benchmarks/bbh/sports_understanding/results/*/
```

### Running all strategies

`scripts/run_all_strategies.sh` runs simulate, unstructured, workflow,
and POT across all benchmarks with consistent minibatch configs:

```bash
bash scripts/run_all_strategies.sh
```

See [docs/CLI.md](docs/CLI.md) for full CLI documentation.

## Requirements

- Python 3.11+
- An API key for your LLM provider (set in `.env`):
  - `GEMINI_API_KEY` for Gemini models
  - `TOGETHER_API_KEY` for Together AI models (DeepSeek, Qwen, etc.)
  - `ANTHROPIC_API_KEY` for Claude models

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the full text.
