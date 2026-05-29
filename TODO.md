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

## Comments

 * lots and lots of loose code in musr

## Caching

 * Keep caches in the benchmark task/subtask directories for now

## Configs

* CLEAN UP deprecated set_root and reset in config.py

* CLEAN UP result configs: DONE
  * in cli/expt.py and config.py
	* paths are set to be relative to project root using the
      ${root.repo}/ syntax.
    * there is also:
	  * root.task that input directories are relative to
	  * root.logs that output directories are relative to
    * someone, maybe Jerry, also introduced a config.get('root') for loading
    * expt.py run can be invoked with --config path/to/results/FOO/config.yaml as an option
	  * the complicated part was loading the ptools.py directory
        * TODO: refactor module loading code, it's duplicated in expt.py and implement/learned_code

* Clean up --evaluator to default to config('evaluate.evaluator_class') which is read with `resolve_dotted` DONE
  * Maybe get rid of the evaluate.match config option? DISCUSS

## Benchmarks

* CLEAN UP benchmarks
  * should be just about running benchmarks, not saving results for the paper
    * thus: benchmarks => COMMON should be moved, to root/paper/results
  * every benchmark should be task/subtask/  - eg bbh/data_understanding - and under that
    * conf
	* data
	* ptools.py
	* Makefile
	* prompt_templates
  * clean up the non-bbh directories to follow the same scheme
  * add benchmark tests for each in benchmarks/tests
	* need to write musr benchmark/tests
    * need to fix the rulearena benchmark/tests
	* need to make the `natural_plan` benchmark/tests follow the `sports_understanding` plan
  * Mostly done except
    - scripts that use old locations might not work - according to claude
	- paper/results is a start at the reorg of results
      - papers/results/results
    - medcalc is an issue
	- rulearena is an issue
    - Legacy scripts (benchmarks/jerry/,
      scripts/orchestrator_learner/, benchmarks/scripts/) still
      reference ptools_murder/object/team/calendar/meeting/trip by
      their old module names. Not in the active critical path but
      they'll break if re-run.
    - rulearena cleanup still pending — needs the test_rulearena.py rewrite (same per-task cwd issue as test_natural_plan).
    - medcalc split still pending — depends on the missing-data/ question (where does medcalc data come from at runtime? a download script? a different repo?).


# Misc Cleanups

 * cli/... - clean up docs for them
 * clean up cli/bench.py
   * Need to think this through, but maybe takes logdir and list of
     `path/to/benchmark_dir` plus dotpair overrides or a config
      * launches parallel jobs that run from benchmark root, each will
	    * load conf `working_dir/conf/conf.yaml` 
	    * make it relative to benchmark root
        * override as needed with dotpair
	      * results, recordings, learned, etc all overridden -> logdir
	      * ....

## From docs/TODO.md

 * add `result.py rename --to '%O_oss2b' results/*` - to help cleanup results
 * look at pot failures and see if there is an easy way to improve them - 
   * Current 2026-04-24 Several easy POT losses appear to be plumbing
     fixes rather than reasoning failures: eg. sandbox/code-extraction
     issues - eg. typing imports being blocked (penguins), fixable by
     replaying the cached generated code with typing allowed. Some
     runs can often return tuples like ("E", "04/11/1985") (especially
     in datetime tasks) when the evaluator wants just (E). There are
     smaller similar issues from blocked json/fractions imports and
     no-code-block outputs. The low hanging fruits seem to be generic
     PoT robustness fixes: allow a few safe imports, improve
     code-block extraction, and normalize final answer shape. MUSR,
     NatPlan and Medcalc Rule failures look like strategy misses, as
     opposed to plumbing
 * What's the use case for llm streaming in llm_util?

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
