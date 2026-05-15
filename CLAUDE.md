# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**secretagent** is a lightweight Python framework for building agentic
systems where "everything looks like code." You define Python stubs
with only a type signature and docstring, and decorate them with
`@interface`.  These stubs are later *bound* to implementations
via `implement_via()` and a registry of `Implementation.Factory` classes
(each Factory subclass overrides `setup()` and `__call__()`).

## Architectural Principles and Terminology

In a complex ML system with many configuration decisions, it's easy to
end up with results that cannot be replicated. Agentic systems are
good examples of this: experimentation is incremental and interactive
and it's easy to get somewhere and not know how you got there.  To
avoid this, secretagent adopts some infrastructure principles that
enable one to **tracks experimentation**, so that one can trace what
was done retrospectively.  This is *not* intended as a substitute for
being systematic and careful when you experiment.

### Strategies are serializable

The behavior of the agentic system is determined by *how the current
set of interfaces are bound to implementations*, which we call the
**implementation strategy**, or just **strategy** for short.

**Every strategy should be serializable** compactly.  Currently, every
implementation is created by a factory, and the arguments for creating
it can be stored in a YAML file.

### Experiments are trackable and reproducible

When running "real" experiments (anything you want to share) **every
experimental result should be tagged with the complete strategy** used
to generate it and the **date** it was created.  "Real" experiments
should be run on a clean copy of the repo's main branch so the date
determines the result of the code.  

The `savefile.py` package is preferred for saving and tracking
experimental results, since it handles this automatically and
consistently.  The `cli.expt.py` and `cli.results.py` tools should
make this easy.

### Learning creates new implementations

Experimentalists can generate new implementations (by prompt tuning,
adding new tools, etc). Learning components in secretagent do the
same.

Learning methods should be in `learn/` and subclass `learn.Learner`.
Learners optionally consume training data, possibly distilled with
another strategy, and outputs **the config information needed to
produce an implementation** of whatever was learned, using an
appropriate registered Factory.  

To make experiments with learned implementations trackable, **learning
should just as trackable** as experimental results are.  The
`learn.Learner` subclass uses `savefile` to store **learned
implementation configs** - that is the main output of any learner.

Learners should also use the `savefile` directory to store relevant
debugging/devel information, like data used in learning, the source of
that data, **the config used in learning**, and so on.  Different
learners will populate different parts of a single `savefile`
directory, and that directory **should encode the complete trajectory
of the learning processes** so it can be reproduced.

### Optimization searches a space of stategies

Optimization methods are used to evaluate existing strategies and
recommend good ones.  So that optimization decisions can be tracked,
the **space searched by an optimizer should be serializable**, and the
**evaluation results produced by an optimizer should be saved for
tracking.**

Optimization and learning perform different and complementary tasks:
learning introduces new potential strategies, optimization evaluates
them.  Optimization and learning could be interleaved.

## Running code: use uv for running code and installing packages

 * Use 'uv run' to run a script.
 * Use 'uv python pin 3.11.9' to make sure python3 runs
 * Use 'uv add FOO' to add a package
 * Use 'uv sync' after a 'git pull' to update the environment
 * Analysis scripts that use matplotlib, pandas, etc are tagged with
   'uv --script FOO.py PACKAGE'
 
## Core API (`secretagent.core`)

 * `@interface` — decorator that turns a stub function into an `Interface`
 * `@implement_via(method, **kw)` — decorator that creates an Interface and binds it in one step
 * `interface.implement_via(method, **kw)` — bind an existing Interface to an implementation
 * `all_interfaces()` — list all registered Interfaces
 * `all_factories()` — list all registered Factory name/instance pairs
 * `register_factory()` - add a new Implementation.Factory to the registery

### Built-in factories (registered in `_FACTORIES`)

 * `'direct'` — use the function body as the implementation
 * `'simulate'` — prompt an LLM to simulate a function call (NOT react, NOT an agent, just a single LLM call to predict function output)
 * `'prompt_llm'` — use a custom prompt template to predict the function
 * `'program_of_thought'` — generate Python code with an LLM and execute it in a sandboxed executor
 * `'simulate_pydantic'` — like simulate but uses a pydantic-ai Agent (in `implement/pydantic.py`)

### Key files

 * `src/secretagent/core.py` — Interface, Implementation, Factory base class
 * `src/secretagent/implement/pydantic.py` — SimulatePydanticFactory (pydantic-ai Agent backend)
 * `src/secretagent/implement/core.py` — built-in factories (direct, simulate, prompt_llm, program_of_thought)
 * `src/secretagent/config.py` — global/local configuration via `configure()` and `configuration()` context manager
 * `src/secretagent/record.py` — recording of interface calls via `recorder()` context manager
 * `src/secretagent/cache_util.py` — runtime cachier wrapper that reads config at call time
 * `src/secretagent/llm_util.py` — low-level LLM call helper
 * `src/secretagent/dataset.py` — Case and Dataset models for evaluation data
 * `src/secretagent/evaluate.py` — Evaluator base class for running experiments on datasets
 * `src/secretagent/cli/` — command-line tools (see below)
 * `tests/` — pytest tests (`test_core.py`, `test_config.py`, `test_record.py`)
 * `examples/` — quickstart.py, sports_understanding.py

## Configuration

This project is heavily configuration-driven, like most ML systems.

 * `src/secretagent/config.py` manages configurations 
 * `config.configure(yaml_file=...)` loads a hierarchical config
   * Dot notation is used for config keys, eg 'llm.model' or 'echo.llm_input'
 * `config.configure(cfg={...})` loads a user-specified config
 * `config.configure(llm=dict(model='gpt-5', echo={...})` also adds specific config values
 * `with config.configuration(echo=dict(service=True, ...)):` is a context manager
 that sets config parameters temporarily and restores them when it exits.

See @docs/CONFIG_KEYS.md

## Caching

Calls to llm models should be routed thru litellm, usually through
llm_util.  Calls can be cached in a directory, which caches output and
other stats (e.g., input/output tokens and cost).

## CLI tools

See @docs/CLI.md

## Coding style

 * Import everything at the top of the file
