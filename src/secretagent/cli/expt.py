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
import importlib.util
import pandas as pd
from pathlib import Path
import pprint
import sys

import typer

from secretagent import record, config
from secretagent.core import implement_via_config, Interface
from secretagent.dataset import Dataset
from secretagent.evaluate import ExactMatchEvaluator, Evaluator
from secretagent.implement.util import resolve_dotted

#
# shared setup logic
#

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}

def _load_module_from_path(module_path: str | Path):
    """Load a Python module from a filesystem path.

    module_path can be a directory (package) or a .py file.  If it's a
    directory, __init__.py is loaded.  The module is registered in
    sys.modules under a unique name derived from the path to avoid
    collisions between different ptools modules.
    """
    module_path = Path(module_path)
    if module_path.is_dir():
        file_path = module_path / '__init__.py'
    elif module_path.suffix == '.py':
        file_path = module_path
    else:
        file_path = module_path.with_suffix('.py')
    if not file_path.exists():
        raise FileNotFoundError(f'Cannot find module at {file_path}')
    # unique key so multiple ptools don't collide in sys.modules
    sys_key = f'_ptools_{file_path.resolve()}'
    if sys_key in sys.modules:
        return sys.modules[sys_key]
    spec = importlib.util.spec_from_file_location(module_path.name, str(file_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[sys_key] = mod
    # also register under the basename so internal imports work
    sys.modules[module_path.name] = mod
    spec.loader.exec_module(mod)
    return mod

def setup_and_load_dataset(dotlist: list[str], config_file: str | Path | None = None) -> Dataset:
    """Load config, dataset, and configure ptools.

    Args:
        dotlist: config overrides in dot notation.
        config_file: YAML config file to load. Defaults to conf/conf.yaml
            in the current directory.

    Returns dataset ready for evaluation.
    """
    root = Path.cwd()
    if config_file is None:
        config_file = root / 'conf' / 'conf.yaml'
    config.configure(yaml_file=config_file, dotlist=dotlist)

    owd = Path(config.get('original_working_dir', '.'))
    split = config.require('dataset.split')
    json_data_dir = Path(config.get('dataset.json_data_dir', str(owd / 'data')))
    dataset_json_file = json_data_dir / f'{split}.json'
    dataset = Dataset.model_validate_json(dataset_json_file.read_text(encoding='utf-8'))
    dataset.configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n') or None  # don't pass in 0
    )
    ptools = _load_module_from_path(config.get('dataset.ptools_module', str(owd / 'ptools')))
    implement_via_config(ptools, config.require('ptools'))
    return dataset

def run_experiment(
        top_level_interface: Interface | None = None,
        dotlist: list[str] | None = None,
        evaluator: Evaluator | None = None,
        config_file: str | Path | None = None,
) -> pd.DataFrame:
    # prevent permanent changes to the config
    with config.configuration():
        dataset = setup_and_load_dataset(dotlist or [], config_file=config_file)
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
    config_file: str = typer.Option(None, "--config", help="YAML config file (default: conf/conf.yaml)"),
    evaluator: str = typer.Option(None, help="Evaluator class as 'module.ClassName'"),
    interface: str = typer.Option(None, help="Top-level interface as 'module.name' (default: from evaluate.root_interface config)"),
):
    """Run a benchmark evaluation.

    Extra args are parsed as config overrides in dot notation, e.g.:
        uv run python -m secretagent.cli.expt run --interface ptools.my_fn llm.model=gpt-4o
    """
    eval_instance = resolve_dotted(evaluator)() if evaluator else None
    top_level = resolve_dotted(interface) if interface else None
    run_experiment(
        top_level_interface=top_level,
        dotlist=ctx.args,
        evaluator=eval_instance,
        config_file=config_file)


def _resolve_case(dataset, case_name):
    """Pick a case by name, or default to the first case."""
    if case_name is None:
        return dataset.cases[0]
    matching = [c for c in dataset.cases if c.name == case_name]
    if not matching:
        print(f'No case named {case_name!r} found in dataset')
        raise typer.Exit(1)
    return matching[0]


@app.command(context_settings=_EXTRA_ARGS)
def quick_test(
    ctx: typer.Context,
    config_file: str = typer.Option(None, "--config", help="YAML config file (default: conf/conf.yaml)"),
    interface: str = typer.Option(None, help="Top-level interface as 'module.name' (default: from evaluate.root_interface config)"),
    case: str = typer.Option(None, help="Case name to run, e.g. valid.006. Defaults to first case."),
):
    """Do a quick test of a configuration.

    Configures and loads data as in the run command, but just runs the
    top-level interface on a single example, tracing as much as
    possible.
    """
    dataset = setup_and_load_dataset(ctx.args, config_file=config_file)
    print('dataset is', dataset.summary())
    top_level = resolve_dotted(interface or config.require('evaluate.root_interface'))
    pprint.pprint(config.GLOBAL_CONFIG)

    test_case = _resolve_case(dataset, case)
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


@app.command(context_settings=_EXTRA_ARGS)
def cached_test(
    ctx: typer.Context,
    config_file: str = typer.Option(None, "--config", help="YAML config file (default: conf/conf.yaml)"),
    interface: str = typer.Option(None, help="Top-level interface as 'module.name' (default: from evaluate.root_interface config)"),
    case: str = typer.Option(None, help="Case name to run, e.g. valid.006. Defaults to first case."),
):
    """Test a configuration on a single example, keeping the LLM cache active.

    Same as quick-test, but does not disable caching — repeat runs reuse
    previously cached LLM calls so iteration on a single case is cheap.
    """
    dataset = setup_and_load_dataset(ctx.args, config_file=config_file)
    print('dataset is', dataset.summary())
    top_level = resolve_dotted(interface or config.require('evaluate.root_interface'))
    pprint.pprint(config.GLOBAL_CONFIG)

    test_case = _resolve_case(dataset, case)
    input_args = test_case.input_args
    print('input_args', input_args)
    with config.configuration(
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
