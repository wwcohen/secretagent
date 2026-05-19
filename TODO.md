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
 * 

## Caching

 * Keep caches in the benchmark task/subtask directories for now

## Configs

* CLEAN UP result configs: DONE
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


