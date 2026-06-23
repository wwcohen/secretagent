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
workflows here.

## Tool bundles with shared state: `ToolFactory`

> Worked example: `benchmarks/musr/murder/` —
> `MurderToolFactory` in `ptools.py`, wired by the `react_factory`
> target in `Makefile`. Read those alongside this section.

A `simulate_pydantic` agent's tools are plain functions, and the agent
has to pass each argument explicitly on every call.  When several tools
share a large input — e.g. a long narrative the agent inspects via many
small probes — repeating that input on every tool call is wasteful and
sometimes simply too long for the model.

A `ToolFactory` lets you bundle a related group of tools whose
per-call state lives on `self`.  A fresh instance is created **per
interface call**; `init()` receives the interface's call arguments and
seeds the state; `tools()` returns the bound methods that the agent
will call.  Because each interface call gets its own instance there is
no cross-call leakage and `evaluate.max_workers > 1` is safe.

### Defining a ToolFactory

Subclass `ToolFactory` (in `secretagent.implement.pydantic`) and
override `init` and `tools`. The bound methods become the agent's tool
set; their docstrings are the prompts the agent reads. See
`benchmarks/musr/murder/ptools.py` for a complete example
(`MurderToolFactory`).

```python
from secretagent.implement.pydantic import ToolFactory

class MyToolFactory(ToolFactory):
    """Tools for solving FOO problems over a shared CONTEXT."""

    def __init__(self):
        self.context: str = ''

    def init(self, context, question, choices):
        # Called once per interface call, BEFORE the agent runs.
        # Receives the same positional args that the top-level interface
        # was called with — store whatever the tools need on self.
        self.context = context

    def my_tool(self, query: str) -> str:
        """Docstring shown to the agent — explain when/how to call this."""
        return do_something(self.context, query)

    def another_tool(self, intermediate: str) -> str:
        """Threads intermediate results between steps."""
        return refine(self.context, intermediate)

    def tools(self):
        return [self.my_tool, self.another_tool]
```

Rules:
- `__init__()` runs once per instance and should set defaults for every
  attribute the bound methods read.  Don't put per-call state there
  unless you also re-initialize it in `init()`.
- `init(*args, **kwargs)` receives whatever the top-level interface was
  called with.  Use an explicit signature matching the interface, e.g.
  `init(self, narrative, question, choices)`, and store only what the
  tools need.
- Bound methods (the things `tools()` returns) are the agent-facing
  tools.  Their docstrings are the only documentation the agent sees,
  so write them as if for the LLM.  Their signatures should NOT include
  the shared state — that's the whole point.

### Wiring a ToolFactory

Bind the `simulate_pydantic` factory with a `tool_factory` kwarg
giving the dotted name of the subclass (resolvable via the loaded
ptools module).  `tool_factory` is mutually exclusive with `tools` /
`tool_module`; you pick one or the other.

In a YAML config:

```yaml
ptools:
  answer_question:
    method: simulate_pydantic
    tool_factory: ptools.MyToolFactory
```

Or as command-line dotpair overrides (e.g. in a Makefile target):

```makefile
react_factory:
	$(EXPT) run evaluate.expt_name=react_factory $(DOTPAIRS) \
	  ptools.answer_question.method=simulate_pydantic \
	  ptools.answer_question.tool_factory=ptools.MyToolFactory
```

At call time `SimulatePydanticFactory.__call__(*args, **kw)` does
roughly:

```python
provider = MyToolFactory()              # fresh per call
provider.init(*args, **kw)              # seed state from interface args
tools = provider.tools()                # bound methods, ready to use
# ... agent runs with `tools` ...
```

### When NOT to use it

If your sub-tools take their arguments naturally (no large shared
input, no per-call mutable state, no pagination cursors), just list
them as plain `tools:` — the `ToolFactory` is for the cases where the
agent would otherwise have to thread one big argument through every
tool call, or where the tools need to share evolving state between
calls.

## Setting up the datasets

In `data/` write code to build three datasets, `train.json`,
`valid.json`, and `test.json`.  Each of these should be a json-serialized  
`Dataset` object.

## Setting up the experiments

You can probably use `secretagent/cli/expt.py`.  (Via uv, so the
command is `uv run python -m secretagent.cli.expt`) Look at
`benchmarks/bbh/sports_understanding/Makefile` for examples of how to
call it.  Each experiment will load the shared configuration from
conf/conf.yaml, and any any experiment-specific configuration params
from the command line.

When you run `expt.py` it will load in `conf/conf.yaml`, which should
have the common information needed by experiments.  Some conventions:
 * resources, like dataset files and ptools, are located relative to
   the directory `${pathto.task}` which should be defined relative to
   `${pathto.repo}`, the project root.  You don't need to define the
   repo root, that is pre-defined before the config is loaded.
 * outputs, like results, learned results, etc, should be defined
   relative to `${pathto.logs}`.  This is sometimes the same as the
   task directory but not always.
 * the cache directory `cachier.cache_dir` is in the task directory,
   so it can be shared across different experiment on the task.

On the `expt.py` command line, you may need to specify to expt.py the
classname of the `Evaluator` you will use, which defaults to checking
for an exact match between predicted and expected outputs.  If you
dont use exact match evaluate responses, you need to subclass
evaluate.Evaluator, and pass that in as `--evaluator foo`.  A minimal
subclass implementation computes one metric by comparing the
`predicted_output` and `expected_output`.

Configs that must be passed to experiment include:
  * `evaluate.expt_name`, which is where the results of the evaluation
      will be filed.
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
