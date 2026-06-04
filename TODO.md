# Cleaning up to allow scalable clean experiments

## New File Layout
```
 | src
 | benchmarks
 |   | bbh 
 |   | | date_understanding
 |   | | ...
 | paper
 |   | experiments
 |   | | expt1
 |   | |   runner.py
 |   | |   hero_table.py
 |   | |   results
 |   | |   | bbh 
```

## Bugs

 * dataset.Cases with input_kws are allowed but not really supported properly
   * probably fixed

## Caching

 * Keep caches in the benchmark task/subtask directories for now

## Configs

* CLEAN UP deprecated set_root and reset in config.py - done

* Make pathto.repo an environment variable => Cassie
  OmegaConf supports environment variable interpolation via the built-in oc.env resolver:

                                                                                                                                 
```
  api_key: ${oc.env:OPENAI_API_KEY}
  model: ${oc.env:MODEL_NAME,gpt-4}   # with default

  The second arg is an optional default if the variable is unset. Works out of the box — no resolver registration needed.
```

  So set up a .env file and initialize it with PATHTO_REPO=...
  (.env is in .gitignore, .env-sample is checked in)

  # then before you config.load_config...

  import os
  from dotenv import load_dotenv
  # Load the variables from the .env file into the system environment
  load_dotenv()
  # now ${oc.env:XXX} will work when you load the config.

* CLEAN UP result configs: DONE
  * in cli/expt.py and config.py
	* paths to be set to be relative to project root using the
      ${oc.env:PATHTO_REPO} syntax.
    * someone, maybe Jerry, also introduced a config.get('root') for loading, need to replace ==> Cassie
	* TODO: refactor module loading code, it's duplicated in expt.py and implement/learned_code

## Benchmarks

* CLEAN UP benchmarks
  * write and
  * clean up the non-bbh directories to follow the same scheme
  * add benchmark tests for each benchmark that we've converted in benchmarks/tests => Cassie
	* need to write musr benchmark/tests
    * need to fix the rulearena benchmark/tests
  * Mostly done except
	- paper/results is a start at the reorg of results => Cassie
      - Goal: approximately reproduce table1 of the paper
        - but on gemini, 3.1-flash-lite, and 3-1-pro
	    - running requires specifying the task inputs and the place to store logs and results and shouldn't change the benchmark/task/subtask
        - want to rerun all the 'basic' strategies and do the
          experiments from the repository root with no logs left in
          the benchmark/task/subtask directories
	      - there's still some config information to collect from
            Makefile I think but we should minimize this, and if we
            need to collect it, put it in the benchmark directories
            not in the code you write.

  * Lower priority:
    - scripts that use old locations might not work - according to claude => Cassie
    - medcalc is an issue
    - Legacy scripts (benchmarks/jerry/,
      scripts/orchestrator_learner/, benchmarks/scripts/) still
      reference ptools_murder/object/team/calendar/meeting/trip by
      their old module names. Not in the active critical path but
      they'll break if re-run.
    - rulearena cleanup still pending — needs the test_rulearena.py rewrite (same per-task cwd issue as test_natural_plan).
    - medcalc split still pending — depends on the missing-data/ question (where does medcalc data come from at runtime? a download script? a different repo?).


# Dependencies

 * Track down dependencies
   * clip, torch?

# Misc Cleanups

 * cli/... - clean up docs for them
 * clean up cli/bench.py => get rid of this? Cassie
   * Need to think this through, but maybe takes logdir and list of
     `path/to/benchmark_dir` plus dotpair overrides or a config
      * launches parallel jobs that run from benchmark root, each will
	    * load conf `working_dir/conf/conf.yaml` 
	    * make it relative to benchmark root
        * override as needed with dotpair
	      * results, recordings, learned, etc all overridden -> logdir
	      * ....

## From docs/TODO.md

 * look at pot failures and see if there is an easy way to improve them - 
 * What's the use case for llm streaming in llm_util?
 * Do we really need multi-threading and such

# Cleaning up the Orchestrate-related code

## `experimental/improve.py` and the `self_improve.py` scripts

### STATUS

 * removed the `self_improve.py` scripts
 * haven't refactored orchestrate to not use `improve_ptool_within_workflow`
   and haven't touched medagentbench

### More detail on orchestrate changes (mostly from Claude)

`src/secretagent/experimental/improve.py` (641 LOC, one file) is
load-bearing despite the `experimental/` name. Active callers:

  * `src/secretagent/orchestrate/transforms/evolve.py` — the
    `evolve` transform delegates to `improve_ptool_within_workflow`.
  * `benchmarks/medcalc/self_improve.py`
  * `benchmarks/natural_plan/self_improve.py`
  * `benchmarks/musr/self_improve.py`
  * `benchmarks/medagentbench/medagentbench/expt.py` — imports
    `improve_ptool_within_workflow`, `_apply_variant`, `_get_ptool_info`,
    `_FitnessTracker`, `_llm_call`, `_extract_code`.

The fact that underscored names (`_FitnessTracker`, `_llm_call`,
`_extract_code`, `_apply_variant`, `_get_ptool_info`) are imported
externally is a smell — the public API hasn't been settled. Worth
either promoting these into a real module under `orchestrate/` (or a
new top-level home) and giving them non-underscored names, or making
medagentbench depend on the higher-level helpers only.

The three benchmark `self_improve.py` scripts (medcalc 214, natural_plan
242, musr 308) are near-clones implementing the same loop.

Per-benchmark differences are only in plumbing: each imports its own
evaluator (`MedCalcEvaluator` / `NaturalPlanEvaluator` / …) and
`setup` / `load_dataset` from the local `expt.py`. Default
`--target-accuracy` differs (medcalc 0.50, natural_plan 0.60).
`musr/self_improve.py` carries some extra glue (Dataset/Case import,
~308 LOC vs ~220).

  TODO:
  * Decide where this lives. `experimental/` is misleading given the
    number of callers; either fold the algorithm into
    `orchestrate/` proper or give it its own subpackage (e.g.
    `self_improve/`).
  * Stop exporting underscored helpers; promote what medagentbench
    needs to public names, or refactor medagentbench to consume only
    the top-level entry point.
  * Consider whether `_pick_weakest_ptool` belongs alongside the
    profiler (it's a profile-consumer, not benchmark-specific).

# Proposal: ToolFactory for per-call tool state

## Problem

Tool-using implementation factories (`SimulatePydanticFactory`,
`PoTFactory`) sometimes need to give their tools per-call state without
forcing the LLM to pass it as an argument on every call. The motivating
case is MUSR ReAct (`benchmarks/musr/ptools_common.py`): the
`search`/`lookup`/`finish` tools need the current narrative, so it's
stashed in a module-global `_REACT_STATE` dict and reset per example.

That global works and has one real virtue — the tools stay
**factory-agnostic**: the same plain `search(query)` function is driven
unchanged by the pydantic-ai agent, by PoT's smolagents code executor
(tools go into `custom_tools` and generated code calls them by name),
and by direct calls. But it relies on sequential evaluation; under
`evaluate.max_workers > 1` the shared dict races across worker threads.

## Options considered

 * **Bound methods on a shared singleton** — cleaner encapsulation than
   a free dict, but a single shared instance is still shared mutable
   state, so it keeps the same cross-worker race.
 * **pydantic-ai `deps` / `RunContext`** — the idiomatic per-call
   injection (`def search(ctx: RunContext[Deps], query)`,
   `agent.run_sync(..., deps=...)`). Concurrency-safe, no global, but
   it's pydantic-ai-specific and **breaks PoT**: the smolagents sandbox
   has no `RunContext` to supply, so the same tool can't serve both
   factories. Forks the tool API along factory lines.
 * **`contextvars.ContextVar`** — factory-agnostic and per-thread/async
   isolated, but doesn't cross the `llm.timeout` nested-`ThreadPoolExecutor`
   boundary without an explicit `copy_context().run(...)`.

## Proposed design

A `ToolFactory` base class, subclassed to define a related set of tools,
with the instance created **per `__call__`** (deferred to call time, not
bind time):

```python
class ToolFactory:
    def init(self, *call_args, **call_kw):
        """Initialize per-call state from the interface's arguments."""
    def tools(self) -> list[Callable]:
        """Return the bound tool methods to hand the agent / sandbox."""

class NarrativeToolFactory(ToolFactory):
    def init(self, narrative, question, choices):
        self.narrative = narrative; self.finish_answer = None; ...
    def search(self, query):  ...    # reads self.narrative
    def lookup(self, string): ...
    def finish(self, answer_index): ...
    def tools(self): return [self.search, self.lookup, self.finish]
```

A fresh instance per call gives per-call state on `self` (no global, no
race), and because the tools are plain bound methods there's no
`RunContext`, so PoT can drop them straight into `custom_tools`. This
threads the needle the three options above each missed: factory-agnostic
+ per-call isolation + no global.

Wiring stays serializable (fits "strategies are serializable"):

```yaml
react_solve:
  method: simulate_pydantic
  tool_factory: ptools_common.NarrativeToolFactory
```

## Changes needed in the consuming factories

 * `__call__` instantiates the resolved `ToolFactory` class per call and
   forwards the interface call args: `provider.init(*args, **kw)`, then
   `tools = provider.tools()`. (The subclass decides which args it needs
   — this forwarding is the load-bearing detail.)
 * Relax `SimulatePydanticFactory.setup()`'s `inspect.isfunction` guard
   to accept bound methods (`callable` / `ismethod`); pydantic-ai accepts
   bound methods and PoT keys on `fn.__name__`, which methods have.
 * Caching is unaffected: `_run_agent_hashkey` keys on
   `tuple(tool.__name__ ...)` + the prompt (which already contains the
   narrative), not on instance identity.

## Sharp edge: out-of-band result extraction

The module global did double duty — feeding state *into* the tools and
carrying a result *back out*. `react_answer_impl`'s recovery ladder reads
`_REACT_STATE['finish_answer']` *after* the agent returns, to survive a
crash-after-`finish`. If the instance is owned inside the impl factory's
`__call__`, the `direct` entry point that called the interface no longer
has a handle to read `finish_answer`. Resolve by either:

 * dropping the recovery hack and trusting the agent's returned index
   (simpler, slightly less robust), or
 * giving `ToolFactory` an explicit `result()` accessor that the impl
   factory surfaces (e.g. via `record.record(...)` or the return value),
   which keeps robustness but re-couples the impl factory to the notion
   of an extractable result.
