"""Sports understanding benchmark experiment.

Example CLI commands:

    # run with defaults from conf/conf.yaml
    uv run python expt.py run

    # run first 6 examples only
    uv run python expt.py run --n 6

    # override model and experiment name
    uv run python expt.py run --model gpt-4o --expt-name gpt4o_test

    # use a different config file
    uv run python expt.py run --config-file conf/ablation.yaml

    # override dataset split
    uv run python expt.py run --split test
"""

import json
import pandas as pd
from pathlib import Path
import re
from typing import Any

import typer

from secretagent import record, config
from secretagent.core import Interface
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator

#
# tools are the tools and interfaces
#

import tools

class SportsUnderstandingEvaluator(Evaluator):

    def measure(self, example: Case, interface: Interface) -> dict[str, Any]:
        with record.recorder() as records:
            result = tools.sports_understanding(*example.input_args)
            llm_usage_stats = self.aggregate_usage_stats(records)
            return dict(
                predicted_output=result,
                expected_output=example.expected_output,
                correct=int(result == example.expected_output),
                **llm_usage_stats)

def load_dataset(split: str) -> Dataset:
    def example_as_case(index, example):
        return Case(
            name=f'ex{index:03d}',
            input_args=(re.search(r'"([^"]*)"', example['input']).group(1),),
            expected_output=(example['target']=="yes")
        )
    json_file = Path(__file__).parent / 'data' / f'{split}.json'
    with open(json_file) as fp:
        data = json.load(fp)
        examples = data['examples']
        return Dataset(
            name='sports_understanding',
            split=split,
            cases=[
                example_as_case(i, ex)
                for i, ex in enumerate(examples)
            ],
        )


#
# machinery to support using this as a CLI
#

app = typer.Typer()

@app.callback()
def callback():
    """Sports understanding benchmark.

    This callback ensures typer treats the app as a multi-command CLI
    rather than collapsing a single subcommand to the top level.
    """

CONF_DIR = Path(__file__).parent / 'conf'

@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": False})
def run(
    ctx: typer.Context,
    model: str = typer.Option(None, help="Override llm.model"),
    split: str = typer.Option(None, help="Override dataset.split"),
    expt_name: str = typer.Option(None, help="Override evaluate.expt_name"),
    n: int = typer.Option(0, help="Number of examples (0 for all)"),
):
    """Run sports understanding evaluation.

    Extra args are parsed as config overrides in dot notation, e.g.:
        uv run python expt.py run llm.model=gpt-4o cachier.enable_caching=false
    """

    config_file =  Path(__file__).parent / 'conf' / 'conf.yaml'
    config.configure(yaml_file=config_file, dotlist=ctx.args)
    config.set_root(Path(__file__).parent)

    dataset = load_dataset(config.require('dataset.split')).configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n'))
    print('dataset is', dataset.summary())

    tools_cfg = config.require('tools')
    for name, tool_cfg in tools_cfg.items():
        tool_cfg = dict(tool_cfg)
        method = tool_cfg.pop('method')
        getattr(tools, name).implement_via(method, **tool_cfg)

    evaluator = SportsUnderstandingEvaluator()
    result = evaluator.evaluate(dataset, tools.sports_understanding)
    df = pd.DataFrame(result)
    print(df)


if __name__ == '__main__':
    app()
