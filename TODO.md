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

* Make pathto.repo an environment variable => Cassie -done??
  Need to check existing conf.yaml files for that - Cassie

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
      RESOLVED 2026-06-10: data is the HuggingFace dataset `ncbi/MedCalc-Bench-v1.2` (CC BY-SA 4.0, not gated). Added a `snapshot-data` command + `make data` that caches it to `benchmarks/medcalc/data/{train,test}.json` (gitignored, ~43MB; see data/ATTRIBUTION.md); `load_dataset` prefers the local snapshot with a live-HF fallback. `test_medcalc.py` DONE 2026-06-15 (no-API + integration tests pass). Remaining: convert medcalc to the full bbh task/subtask shape — deferred as a design call (per-category split vs keep single-task; see PERSONAL_TODO 2026-06-15).


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

# Code-review findings (2026-06-09, Claude cleanup pass)

Found during a thorough src/ review. Each was verified by reading the
code. Five small, isolated bugs were already fixed (config.configuration
try/finally; PTP $schema_block KeyError; GA crossover doc/src restore;
debug replay input_kw; Dataset.tail count) — the items below are the ones
left to do, needing more judgment or touching shared/research code.

## Bugs (not yet fixed)

 * `learnedcode._load_learned_module` skips `sys.modules` registration
   (implement/learnedcode.py:14), so classes from a `learned.py` won't
   pickle — breaks caching their output. It's one of three divergent
   copies of the loader; fix via the consolidation below (this is the
   "refactor module loading code" item under Configs).
 * `improve_pipeline` regression branch doesn't roll back
   (orchestrate/improve.py:147): a rejected iteration leaves global
   `config` and rebound ptools mutated, so the next iteration profiles
   dirty state. `improve_with_supervisor` rolls back correctly; this
   loop doesn't.
 * `PruneTransform` can never fire: `PtoolProfile.lift` is never
   populated by `profile_from_results` (profiler.py:155) but
   `should_apply` requires `lift is not None` (prune.py:28). Either
   compute lift per ptool or change the trigger.
 * `RepairTransform` feeds the LLM an empty profile
   (repair.py:96): `format_profiling_summary(PipelineProfile(accuracy=0.0,
   ptool_profiles={}))` — the prompt says "accuracy 0.0%, no breakdown".
   Pass the real profile through.
 * `SelfConsistencyFactory` records `stats={}` (selfconsistency.py:99):
   N billed LLM calls are reported as zero cost/latency. Aggregate the
   per-sample stats (cf. pydantic.py which records NaN, not 0).

## Duplication / refactors

 * Three divergent dynamic module loaders: `expt._load_module_from_path`
   (cli/expt.py:42, most complete), `learnedcode._load_learned_module`
   (no sys.modules reg — see bug above), `util._load_module_from_file`
   (fixed-name reg). Consolidate on one. (== the Configs "refactor module
   loading code" TODO.)
 * `_get_dirs` is byte-identical in cli/results.py:76 and cli/debug.py:28
   — trivial to share.
 * learn/ distill round-loop is ~50 near-identical lines in
   codedistill.py:259 vs workflow_distill.py:501; the holdout-split is
   duplicated three times (learn/base.py, codedistill.py,
   workflow_distill.py). Extract shared helpers.
 * evaluate.py builds the same skipped-case failure-row dict three times
   (evaluate.py:110-168); cli/results.py repeats the metric-default +
   parse_metrics + read-CSV preamble in 5 commands.

## Low-priority dead code

 * composer `_extract_last_function_body` is unused (composer.py:233) and
   its `entry_signature` arg (also unused in `_strip_def_line`).
 * vlm.py threads a dead `output_mode` param into `_call_vlm_impl`.
 * pydantic.py `_run_agent_impl` reassigns its `return_type` arg before
   use (cache key keys on the passed value — confusing, not yet a bug).
 * Stub transforms expand/induce/restructure raise NotImplementedError
   but are registered; induce/restructure return should_apply=True every
   iteration (no-op work each loop).

## Regression tests added (done this pass)

 * New `tests/test_ptp.py` — first PTP coverage; locks the `$schema_block`
   KeyError fix (create_prompt builds with/without a pydantic return type).
 * New stubbed PoT plumbing test in `tests/test_pot.py`
   (`test_pot_executes_and_records_generated_code_stubbed`): runs the
   sandbox + checks recorded code deterministically, no API key. Also fixed
   the stale `test_create_prompt_includes_pydantic_tool_schema` (now asserts
   class-source output, matching `_format_pydantic_schema`).
 * `tests/test_config_extras.py` — `config.configuration` restore-on-exception
   (the finally fix) + template resolution via `pathto.task` / `pathto.repo`.
 * `tests/test_dataset.py` — `tail()` prints the discarded count.
 * `tests/conftest.py` — `needs_api_key` now accepts any of ANTHROPIC /
   GEMINI / TOGETHER_API_KEY / TOGETHERAI_API_KEY (Together-only no longer
   wrongly skipped).
 * Suite: 399 passed, 15 skipped offline (the 15 are live @needs_api_key
   integration tests, skipped only when keys are unset).

## Test issues (fixed this pass)

 * Fixed: `test_resolve_tools_all` now selects '__all__' wrappers by name
   instead of calling every tool, so a leaked 2-arg interface no longer
   breaks it. Added a defensive conftest `_isolate_interfaces` fixture and
   a `teardown_module` in test_evaluate to evict its module-level stubs.
 * Fixed: the 5 `set_root` tests are now OS-agnostic (Path() comparison +
   OS-absolute paths) instead of asserting POSIX separators.

## Test coverage gaps (regression tests still missing)

 * Two of the five bugs fixed in f77cae8f have no direct regression test:
   - cli/debug.py `replay` forwarding `input_kw` (covered only indirectly
     via concat_kw at the Evaluator level).
   - experimental/improve.py crossover restoring `doc`/`src`.
   Both need heavier harnessing (a CLI result dir / a full GA workflow).
   Add when convenient.

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

# Proposal: ToolFactory for per-call tool state (William)

Status:
 * Implemented in `simulate_pydantic` (commit bded5cac). Setup accepts a
   `tool_factory` kwarg (dotted class name, mutually exclusive with
   `tools`/`tool_module`); each `__call__` instantiates the class, runs
   `init(*args, **kw)`, and uses `tools()` as the agent's tool list.
   No-API tests in `tests/test_pydantic_impl.py` cover the mechanism
   (per-call isolation verified by stubbing `_run_agent`).
 * MUSR React path migrated: search/lookup/finish are now bound methods
   on `NarrativeToolFactory` (`benchmarks/musr/ptools_common.py`).
   `_REACT_STATE` retained for the engineered-React path and
   learner-induced ptools that still read it directly.
 * Murder uses its own `MurderToolFactory` (engineered tools auto-pass
   the narrative); see `benchmarks/musr/murder/ptools.py` and the
   `react_factory:` target in that benchmark's Makefile.
 * HOWTO section: "Tool bundles with shared state: ToolFactory" in
   `benchmarks/HOWTO.md`.

## Followups

 * Support `tool_factory` in `PoTFactory` (`src/secretagent/implement/core.py`).
   Mechanical wiring is small — instantiate per `__call__`, drop the
   bound methods into `python_executor.custom_tools` keyed by
   `fn.__name__`. The lift is the prompt: PoTFactory currently renders
   tool stubs from `Interface.src`, so it needs a parallel path that
   synthesizes stubs from `inspect.signature(method)` + `method.__doc__`
   + a return-annotation walk for referenced pydantic models. Estimate:
   half a day, ~30-50 LOC of new helper.
 * Engineered-React path in MUSR object/team still uses `_REACT_STATE`
   for narrative access in the per-task `solve_*` wrappers
   (`benchmarks/musr/{object,team}/ptools.py`). Migrate them to a per-task
   `ToolFactory` subclass (parallel to `MurderToolFactory`).
 * Learner template: `ptool_inducer.py`'s `--state-module` /
   `--state-expr` flags generate code that reads `_REACT_STATE[...]`
   directly. Update the generator to emit a `ToolFactory` subclass
   instead, so newly-induced ptools are concurrency-safe.
 * Decide whether ToolFactory's per-call configuration method should
   stay as `init` or fold into `__init__` (let the subclass take the
   call args as constructor args, so `tool_factory_cls(*args, **kw)`
   replaces the two-step `cls()` + `provider.init(...)`).

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
