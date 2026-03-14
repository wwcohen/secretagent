# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Use uv for running code and installing packages

 * Use 'uv run' to run a script.
 * Use 'uv python pin 3.11.9' to make sure python3 runs
 * Use 'uv add FOO' to add a package
 * Use 'uv sync' after a 'git pull' to update the environment
 * Analysis scripts that use matplotlib, pandas, etc are tagged with
   'uv --script FOO.py PACKAGE'
 
## Project Overview

**secretagent** is a lightweight Python framework for building agentic
systems where "everything looks like code." You define Python stubs
with only a type signature and docstring, and decorate them with
`@interface`.  These stubs are later *bound* to implementations
via `implement_via()` and a registry of `Implementation.Factory` classes.

## Configuration

 * `src/secretagent/config.py` manages configurations 
 * `config.configure(yaml_file=...)` loads a hierarchical config
   * Dot notation is used for config keys, eg 'llm.model' or 'echo.llm_input'
 * `config.configure(cfg={...})` loads a user-specified config
 * `config.configure(llm=dict(model='gpt-5', echo={...})` also loads specific config values
 * `with config.configuration(echo=dict(service=True, ...)):` is a context manager
 that sets config parameters temporarily and restores them when it exits.

### Configuration keys

 * `llm.model` — LLM model name passed to litellm (e.g. `claude-haiku-4-5-20251001`)
 * `llm.thinking` — if truthy, include `<thought>` scaffolding in simulate prompts
 * `echo.model` — print which model is being called
 * `echo.llm_input` — print the prompt sent to the LLM in a box
 * `echo.llm_output` — print the LLM response in a box
 * `echo.code_eval_output` — print result of executing LLM-generated code
 * `echo.service` — print service information
 * `echo.call` — print function call signatures (used by EchoFactory)
 * `evaluate.expt_name` — name tag for the experiment (used in result filenames and dataframes)
 * `evaluate.result_dir` — directory to save results CSV and config YAML snapshot
 * `cachier.enable_caching` — if `False`, bypass cachier entirely (default `True`)
 * `cachier.cache_dir` — directory for cachier's on-disk cache
 * Other `cachier.*` keys are passed through to `@cachier()` (e.g. `stale_after`, `allow_none`)

 * By convention:
   * Everyone accesses the global config, rather than passing down
     pieces of it as arguments.  Instead use the `with configuration`
     context manager.
   * Fail early when required parameters are missing: When a
   configuration parameter is needed by a subroutine, the caller
   should access that param with 'config.require' and pass down the
   required values as a parameter.

### Some useful llm.model values

 * `claude-haiku-4-5-20251001` - quick cheap and stable, needs Anthropic API key
 * `deepseek-v3-0324` - cheap but strong reasoning model

### Core API (`secretagent.core`)

 * `@interface` — decorator that turns a stub function into an `Interface`
 * `@implement_via(method, **kw)` — decorator that creates an Interface and binds it in one step
 * `interface.implement_via(method, **kw)` — bind an existing Interface to an implementation
 * `all_interfaces()` — list all registered Interfaces
 * `all_factories()` — list all registered Factory name/instance pairs
 * `register_factory()` - add a new Implementation.Factory to the registery

### Built-in factories (registered in `_FACTORIES`)

 * `'direct'` — use the function body as the implementation
 * `'simulate'` — prompt an LLM to predict the function output (uses `llm_util`)
 * `'prompt_llm'` — use a custom prompt template to predict the function
 * `'program_of_thought'` — generate Python code with an LLM and execute it in a sandboxed executor
 * `'simulate_pydantic'` — like simulate but uses a pydantic-ai Agent (in `implement_pydantic.py`)

### Key files

 * `src/secretagent/core.py` — Interface, Implementation, Factory base class, and built-in factories
 * `src/secretagent/implement_pydantic.py` — SimulatePydanticFactory (pydantic-ai Agent backend)
 * `src/secretagent/implement_core.py` — built-in factories (direct, echo, simulate, prompt_llm)
 * `src/secretagent/config.py` — global/local configuration via `configure()` and `configuration()` context manager
 * `src/secretagent/record.py` — recording of interface calls via `recorder()` context manager
 * `src/secretagent/cache_util.py` — runtime cachier wrapper that reads config at call time
 * `src/secretagent/llm_util.py` — low-level LLM call helper
 * `src/secretagent/dataset.py` — Case and Dataset models for evaluation data
 * `src/secretagent/evaluate.py` — Evaluator base class for running experiments on datasets
 * `tests/` — pytest tests (`test_core.py`, `test_config.py`, `test_record.py`)
 * `examples/` — quickstart.py, sports_understanding.py
