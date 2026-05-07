"""MUSR benchmark experiment.

Example CLI commands:

    # download data first (from project root)
    uv run benchmarks/musr/data/download.py

    # run murder mystery workflow (default config)
    uv run python benchmarks/musr/expt.py run --config-file conf/murder.yaml

    # run first 10 examples
    uv run python benchmarks/musr/expt.py run --config-file conf/murder.yaml dataset.n=10

    # zero-shot (override workflow to simulate)
    uv run python benchmarks/musr/expt.py run --config-file conf/murder.yaml ptools.answer_question.method=simulate evaluate.expt_name=murder_zeroshot

    # agent loop (program of thought)
    uv run python benchmarks/musr/expt.py run --config-file conf/murder.yaml ptools.answer_question.method=program_of_thought evaluate.expt_name=murder_agent

    # object placement
    uv run python benchmarks/musr/expt.py run --config-file conf/object.yaml

    # team allocation
    uv run python benchmarks/musr/expt.py run --config-file conf/team.yaml
"""

import ast
import importlib
import json
import sys
import pandas as pd
from pathlib import Path
from typing import Any

# Allow running from any directory: add project src/ and this benchmark dir to path
_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

import typer

from secretagent import config
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator

_BASE_SPLIT_TO_MODULE = {
    'murder_mysteries': 'ptools_murder',
    'object_placements': 'ptools_object',
    'team_allocation': 'ptools_team',
}

def _resolve_module(split: str) -> str:
    """Map split name (possibly with _train/_val/_test suffix) to module."""
    for base, module in _BASE_SPLIT_TO_MODULE.items():
        if split == base or split.startswith(base + '_'):
            return module
    raise KeyError(f'Unknown split: {split}')


class MUSREvaluator(Evaluator):
    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        return dict(correct=(predicted_output == expected_output))


def load_dataset(split: str) -> Dataset:
    json_file = Path(__file__).parent / 'data' / f'{split}.json'
    with open(json_file) as f:
        data = json.load(f)

    cases = []
    for i, ex in enumerate(data['examples']):
        choices = ex['choices']
        if isinstance(choices, str):
            choices = ast.literal_eval(choices)
        cases.append(Case(
            name=f'ex{i:03d}',
            input_args=(ex['narrative'], ex['question'], choices),
            expected_output=ex['answer_index'],
        ))

    return Dataset(name='musr', split=split, cases=cases)


app = typer.Typer()

@app.callback()
def callback():
    """MUSR benchmark."""

@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def run(ctx: typer.Context,
        config_file: str = typer.Option(..., help="Config YAML file")):
    """Run MUSR evaluation. Extra args are config overrides in dot notation."""

    # Resolve config_file relative to benchmark dir if not absolute
    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path
    config.configure(yaml_file=str(cfg_path), dotlist=ctx.args)
    config.set_root(_BENCHMARK_DIR)

    split = config.require('dataset.split')
    ptools = importlib.import_module(_resolve_module(split))
    implement_via_config(ptools, config.require('ptools'))

    dataset = load_dataset(split).configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n'))
    print('dataset:', dataset.summary())

    entry_point = config.require('evaluate.entry_point')
    interface = getattr(ptools, entry_point)

    evaluator = MUSREvaluator()
    csv_path = evaluator.evaluate(dataset, interface)
    df = pd.read_csv(csv_path)
    print(f'\nAccuracy: {df["correct"].mean():.1%} ({df["correct"].sum()}/{len(df)})')


if __name__ == '__main__':
    app()
