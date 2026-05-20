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

* CLEAN UP result configs: STARTED
  * CHANGES in cli/expt.py
    * TODO: tests for the changes, adding evaluate.TIMESTEP to the config automatically
    * --interface XXXX now defaults to evaluate.root_interface
	  * TODO: get rid of it
    * set_root is not called on load
	  * TODO: get rid of it
	* paths are set to be relative to project root (marked with
      .root-sentinel.txt file) when configs are written
      * also original_working_dir is set 
        * someone, maybe Jerry, also introduced a config.get('root') for loading
	      prompts from a directory, I switches this to "config.get('root') or config.get('original_working_dir')"
    * expt.py run can be invoked with --config path/to/results/FOO/config.yaml as an option
	  * the complicated part was loading the ptools.py directory
        * TODO: refactor module loading code, it's duplicated in expt.py and implement/learned_code
* TODO:
 * config files should specify separate input/output locations, OmegaConf can handle this:
```
   root:                                                                                                                                                                            
    task: benchmarks/bbh/sports_understanding                                                                                                                                      
    log: papers/experiments/hero_table/logs                                                                                                                                        
                                                                                                                                                                                   
  dataset:                                                                                                                                                                         
    data_json_dir: ${root.task}/data
                                                                                                                                                                                   
  evaluate:                                                                                                                                                                      
    result_dir: ${root.log}/results
```

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
  * Mostly done except
    - scripts that use old locations might not work - according to claude
	- paper/results is a start at the reorg of results
      - papers/results/results
    - medcalc is an issue
	- rulearena is an issue???
    - test_natural_plan.py 
	  — TASK_CONFIG constants updated to new paths, but the
      surrounding _import_modules / _run_eval framework still does
      os.chdir(NATURAL_PLAN_DIR) and loads ptools from the task-set
      dir. Needs a rewrite for the per-task cwd model. Tests fail
      until then.
      - this might be workable with the new expt.py 
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
 * Current 2026-04-24  Several easy POT losses appear to be plumbing fixes rather than reasoning failures: eg. sandbox/code-extraction issues - eg. typing imports being blocked (penguins), fixable by replaying the cached generated code with typing allowed. Some runs can often return tuples like ("E", "04/11/1985") (especially in datetime tasks) when the evaluator wants just (E). There are smaller similar issues from blocked json/fractions imports and no-code-block outputs. The low hanging fruits seem to be generic PoT robustness fixes: allow a few safe imports, improve code-block extraction, and normalize final answer shape. MUSR, NatPlan and Medcalc Rule failures look like strategy misses, as opposed to plumbing
 * What's the use case for llm streaming in llm_util?
 * More guidance for claude/devs on defensive programming


# Cleaning up the Orchestrate-related code

## `experimental/improve.py` and the `self_improve.py` scripts

### STATUS

 * removed the `self_improve.py` scripts
 * haven't refactored orchestrate to not use `improve_ptool_within_workflow`
   and haven't touched medagentbench

### More detail (mostly from Claude)

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

## Relationship to `learn/orchestrate_learner.py`

There are currently **two independent self-improvement implementations**
in the repo, doing roughly the same thing:

  1. **`learn/orchestrate_learner.py`** (1,355 LOC) — the "real"
     learner. Driven via `secretagent.cli.orchestration_learner` and
     the `scripts/orchestrator_learner/*.sh` sweep (15 benchmarks:
     finqa, medcalc, 3 musr splits, 3 natural_plan splits, 3
     rulearena splits, tabmwp, sports/geometric/penguins).
     Supervisor LLM (Gemini Pro) + actor LLM (Gemini Flash Lite)
     iteratively analyzes failures, proposes code edits, hill-climbs
     on accuracy with rollback. Output is a savefile-tracked dir:
     `<bench>/results/orchestration_learner/<timestamp>.orch_learner/`
     with `config.yaml`, `implementation.yaml`, `run_metadata.json`,
     `iterations/iter_*/ptools_{before,after}.py`, `ptools_evolved.py`,
     HTML report. Two "classes": `existing_workflow` and
     `seed_from_ptools` (--seed-orchestrate, seeded from induced
     ptools). `summarize_induced_seed_sweep.py` cross-tabulates runs
     against test results via `run_metadata.json`.

  2. **`experimental/improve.py`** + `self_improve.py` (641 + ~750
     LOC) — the lighter pathway described above. No supervisor
     model, no savefile tracking, output is just
     `benchmarks/<bench>/evolved/<timestamp>.<ptool>/{evolved.py,
     metadata.json}`. Only three benchmark drivers
     (medcalc/natural_plan/musr) plus medagentbench consuming the
     underscored helpers directly.

The framing question for cleanup isn't only "where should
`improve.py` live" — it's **"should `improve.py` exist at all?"**
The orchestrator_learner is Factory-registered, savefile-tracked,
swept across all 15 benchmarks, and follows the CLAUDE.md "learning
creates new implementations" pattern. The `self_improve.py` pathway
looks like an earlier/parallel exploration that never got
generalized.

  TODO (rephrased):
  * Audit what `experimental/improve.py` does that
    `learn/orchestrate_learner.py` does *not* (e.g. evolutionary
    population×generations + Pareto vs. supervisor-driven single-edit
    iteration — are both modes actually needed?).
  * If orchestrate_learner subsumes it: migrate
    `orchestrate/transforms/evolve.py`, medagentbench, and the three
    `self_improve.py` drivers to the orchestrator_learner pathway,
    then delete `experimental/`.
  * If both modes are needed: name the distinction
    (e.g. `learn/evolutionary_improver.py` vs.
    `learn/orchestrate_learner.py`) and stop hiding one under
    `experimental/`.
