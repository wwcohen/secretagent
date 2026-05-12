# Setting up a benchmark

This is a work-in-progress!

## Directory structure

Your directory structure will look something like this:
```
├── conf
│   └── conf.yaml      # configuration settings used in all or most experiments
├── data
│   ├── ...
│   ├── BACKSTORY.md   # provenance of the data
│   ├── test.json      # should have train/test/validation splits
│   ├── train.json
│   └── valid.json
├── expt.py            # your driver program
├── llm_cache          # caches llm calls
├── Makefile           # optional, for repeated tasks
├── prompt_templates   # optional, if you have hand-constructed prompts
│   └── zeroshot.txt
├── ptools.py          # ptools and code implementations of ptools for this benchmark
└── results            # results from runs of expt.py
    ├── 20260316.183513.workflow
    │   ├── config.yaml
    │   ├── results.csv
    │   └── results.jsonl
    ├└── 20260316.183519.pot
    ... ├── config.yaml
        ├── results.csv
        └── results.jsonl
```
## Defining the interfaces

Use `ptools.py` to define the top-level Interface for problems in this
dataset, and any ptools that will used.  Also put hand-coded tools or
workflows here

## Setting up the datasets

In `data/` write code to build three datasets, `train.json`,
`valid.json`, and `test.json`.  Each of these is a json-serialized  
`Dataset` object.


## Setting up the experiments

You can probably use `secretagent/cli/expt.py`.  Look at
`benchmarks/bbh/sports_understanding/Makefile` for examples of how to
call it.  Each experiment will load the shared configuration from
conf/conf.yaml, and any any experiment-specific configuration params
from the command line.  Things that must be passed in include:
    * the top-level interface, passed in as `--interface glob` to expt.py
	* optionally the classname of the `Evaluator` you will use, which
      defaults to checking for an exact match between predicted and
      expected outputs.
       * If you dont use exact match evaluate responses, you need to
	     subclass evaluate.Evaluator, and pass that in as `--evaluator
	     foo`.  A minimal subclass implementation computes one metric
	     by comparing the `predicted_output` and `expected_output`.

Configs that must be passed in include:
	* `evaluate.expt_name`, which is where the results of the
      evaluation will be filed.
    * implementations for all the ptools (if they are not the default
	  specified in the shared config)

## Viewing results

 * To see the most recent experiment for every expt_name, run
   * `uv run python -m secretagent.cli.results average --metric <YOUR METRIC> --metric cost results/*`
 * Other options for the `cli.results` tool are
   * `pair` - run paired tests (the p values should be < 0.05 for differences to be significant)
   * `compare` - review the config options that differ in the selected runs

All of the `cli.results` calls end with a list of `results` directories, which you can specify with 
a `results/*` glob or with a more specific file list.  They can also be modified by arguments before
the list directories:

The argument `--check config.param=value` restricts the list to ones with the specified config params.
Multiple `--check` args can be used to check multiple values.

The argument `--latest k` means to consider the `k` most recent
directories for each expt_name, instead of the single most recent one.

## Exporting results

When you are ready to share results of your experiments, use the `export` subcommand of results.

```
uv run -m secretagent.cli.results export [--latest K] [--check KEY=VALUE] [--as RELATIVE_PATH] DIRS...
```

When you run this from a directory like
`benchmarks/bbh/sports_understanding` it will copy the results you
specify into `paper/results/results/bbh/sports_understanding`, where
`paper/results/results` will be tracked in git.  If you're not organizing
your problems as `benchmarks/TASK/SUBTASK` then you can use `--as
TASK/SUBTASK` to specify where they will be copied to.
