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

### Core API (`secretagent.core`)

 * `@interface` — decorator that turns a stub function into an `Interface`
 * `@implement_via(method, **kw)` — decorator that creates an Interface and binds it in one step
 * `iface.implement_via(method, **kw)` — bind an existing Interface to an implementation
 * `all_interfaces()` — list all registered Interfaces
 * `all_factories()` — list all registered Factory name/instance pairs

### Built-in factories (registered in `_FACTORIES`)

 * `'direct'` — use the function body as the implementation
 * `'echo'` — print the call signature (useful for debugging)
 * `'simulate'` — prompt an LLM to predict the function output (uses `llm_util`)
 * `'simulate_pydantic'` — like simulate but uses a pydantic-ai Agent (in `pydantic_impl.py`)

### Key files

 * `src/secretagent/core.py` — Interface, Implementation, Factory base class, and built-in factories
 * `src/secretagent/pydantic_impl.py` — SimulatePydanticFactory (pydantic-ai Agent backend)
 * `src/secretagent/config.py` — global/local configuration via `configure()` and `configuration()` context manager
 * `src/secretagent/record.py` — recording of interface calls via `recorder()` context manager
 * `src/secretagent/llm_util.py` — low-level LLM call helper
 * `tests/` — pytest tests (`test_core.py`, `test_config.py`, `test_record.py`)
 * `examples/` — quickstart.py, sports_understanding.py
