# secretagent

Lightweight Python framework for building agentic systems where
everything looks like code.

You define Python stubs with only a type signature and docstring,
decorate them with `@interface`, and bind them to implementations
via `implement_via()` and a registry of factories.

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
import secretagent.implement_pydantic  # registers simulate_pydantic factory

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

- `'direct'` -- use the function body as the implementation
- `'echo'` -- print the call signature (debugging)
- `'simulate'` -- prompt an LLM to predict the function output
- `'prompt_llm'` -- use a custom prompt template
- `'simulate_pydantic'` -- like simulate but uses a pydantic-ai Agent

## Benchmarks

Benchmarks live in `benchmarks/` and use a typer CLI with YAML config:

```bash
cd benchmarks/sports_understanding

# run with defaults from conf/conf.yaml
uv run python expt.py run

# override options
uv run python expt.py run --model gpt-4o --n 6

# dot-notation config overrides
uv run python expt.py run llm.model=gpt-4o cachier.enable_caching=false
```

## Requirements

- Python 3.11+
- An API key for your LLM provider (e.g. `ANTHROPIC_API_KEY`)
