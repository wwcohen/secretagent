"""Generic benchmark experiment runner.

Run from a benchmark directory that contains a conf/conf.yaml, a data/
subdirectory, and a ptools module.

Example CLI commands (from a benchmark directory)::

    # run with defaults from conf/conf.yaml
    uv run python -m secretagent.cli.expt run

    # run first 6 examples only
    uv run python -m secretagent.cli.expt run dataset.n=6

    # override model and experiment name
    uv run python -m secretagent.cli.expt run llm.model=gpt-4o evaluate.expt_name=gpt4o_test

    # use a custom evaluator
    uv run python -m secretagent.cli.expt run --evaluator mymodule.MyEvaluator
"""

import importlib
import pandas as pd
from pathlib import Path
import pprint

import typer

from secretagent import record, config
from secretagent.core import implement_via_config, Interface
from secretagent.dataset import Dataset
from secretagent.evaluate import ExactMatchEvaluator, Evaluator
from secretagent.implement.core import resolve_dotted

#
# shared setup logic
#

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}

def setup_and_load_dataset(dotlist: list[str]) -> Dataset:
    """Load config, dataset, and configure ptools.

    Returns dataset ready for evaluation.
    """
    root = Path.cwd()
    config_file = root / 'conf' / 'conf.yaml'
    config.configure(yaml_file=config_file, dotlist=dotlist)
    config.set_root(root)

    split = config.require('dataset.split')
    dataset_json_file = root / 'data' / f'{split}.json'
    dataset = Dataset.model_validate_json(dataset_json_file.read_text())
    dataset.configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n') or None  # don't pass in 0
    )
    ptools = importlib.import_module('ptools')
    implement_via_config(ptools, config.require('ptools'))
    return dataset

def run_experiment(
        top_level_interface: Interface,
        dotlist: list[str] | None = None,
        evaluator: Evaluator | None = None
) -> pd.DataFrame:
    # prevent permanent changes to the config
    with config.configuration():
        dataset = setup_and_load_dataset(dotlist or [])
        evaluator = evaluator or ExactMatchEvaluator()
        csv_path = evaluator.evaluate(dataset, top_level_interface)
        # print a summary
        df = pd.read_csv(csv_path)
        print(df)
        print()
        print(df.select_dtypes(include='number').mean())
        return df

#
# machinery to support using this file as a CLI
#

app = typer.Typer()

@app.command(context_settings=_EXTRA_ARGS)
def run(
    ctx: typer.Context,
    evaluator: str = typer.Option(None, help="Evaluator class as 'module.ClassName'"),
    interface: str = typer.Option(..., help="Top-level interface as 'module.name'"),
):
    """Run a benchmark evaluation.

    Extra args are parsed as config overrides in dot notation, e.g.:
        uv run python -m secretagent.cli.expt run --interface ptools.my_fn llm.model=gpt-4o
    """
    eval_instance = resolve_dotted(evaluator)() if evaluator else None
    top_level = resolve_dotted(interface)
    run_experiment(
        top_level_interface=top_level,
        dotlist=ctx.args,
        evaluator=eval_instance)


@app.command(context_settings=_EXTRA_ARGS)
def quick_test(
    ctx: typer.Context,
    interface: str = typer.Option(..., help="Top-level interface as 'module.name'"),
    case: str = typer.Option(None, help="Case name to test, e.g. 'valid.027'"),
):
    """Do a quick test of a configuration.

    Configures and loads data as in the run command, but just runs the
    top-level interface on a single example, tracing as much as
    possible.
    """
    dataset = setup_and_load_dataset(ctx.args)
    print('dataset is', dataset.summary())
    top_level = resolve_dotted(interface)
    pprint.pprint(config.GLOBAL_CONFIG)

    if case:
        matching = [c for c in dataset.cases if c.name == case]
        if not matching:
            print(f'No case named {case!r} found in dataset')
            raise typer.Exit(1)
        test_case = matching[0]
    else:
        test_case = dataset.cases[0]
    input_args = test_case.input_args
    print('input_args', input_args)
    with config.configuration(
            cachier={'enable_caching': False},
            echo={
                'model': True,
                'llm_input': True, 'llm_output': True,
                'code_eval_input': True, 'code_eval_output': True}
    ):
        with record.recorder() as records:
            predicted_output = top_level(*input_args)
    print('predicted output', predicted_output)
    pprint.pprint(records)


if __name__ == '__main__':
    app()
