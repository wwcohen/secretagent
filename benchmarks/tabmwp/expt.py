"""TabMWP benchmark experiment.

Example CLI commands:

    # download data first (from project root)
    uv run benchmarks/tabmwp/data/download.py

    # structured baseline (single simulate call on top-level interface)
    uv run python benchmarks/tabmwp/expt.py run --config-file conf/structured_baseline.yaml

    # unstructured baseline (vanilla zero-shot prompt, no Python-stub framing)
    uv run python benchmarks/tabmwp/expt.py run --config-file conf/unstructured_baseline.yaml

    # in-context workflow
    uv run python benchmarks/tabmwp/expt.py run --config-file conf/workflow_incontext.yaml

    # tool-based workflow
    uv run python benchmarks/tabmwp/expt.py run --config-file conf/workflow_tools.yaml

    # program of thought
    uv run python benchmarks/tabmwp/expt.py run --config-file conf/pot.yaml

    # react agent with tools
    uv run python benchmarks/tabmwp/expt.py run --config-file conf/react.yaml

    # orchestrated pipeline
    uv run python benchmarks/tabmwp/expt.py run --config-file conf/orchestrated.yaml

    # override n and model
    uv run python benchmarks/tabmwp/expt.py run --config-file conf/unstructured_baseline.yaml dataset.n=10 llm.model=claude-haiku-4-5-20251001

    # quick test (single example, verbose)
    uv run python benchmarks/tabmwp/expt.py quick-test --config-file conf/unstructured_baseline.yaml
"""

import json
import pprint
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import typer

# Allow running from any directory: add project src/ and this benchmark dir to path
_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config, record
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator


import ptools

# ---------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------

SPLIT_TO_FILE = {
    'train': 'problems_train.json',
    'dev': 'problems_dev.json',
    'test': 'problems_test.json',
    'dev1k': 'problems_dev1k.json',
    'test1k': 'problems_test1k.json',
}


def load_raw_data(split: str) -> dict:
    """Load raw TabMWP JSON data for a split."""
    filename = SPLIT_TO_FILE[split]
    json_file = _BENCHMARK_DIR / 'data' / filename
    with open(json_file) as f:
        return json.load(f)


def load_dataset(split: str) -> Dataset:
    """Load TabMWP data as a Dataset of Cases.

    Each Case has input_args = (question, table, table_id, choices)
    matching the tabmwp_solve interface signature.
    """
    data = load_raw_data(split)

    cases = []
    for ex_id, ex in data.items():
        cases.append(Case(
            name=ex_id,
            input_args=(ex['question'], ex['table'], ex_id, ex['choices']),
            expected_output=str(ex['answer']),
            metadata={
                'ques_type': ex.get('ques_type'),
                'ans_type': ex.get('ans_type'),
                'grade': ex.get('grade'),
            },
        ))

    return Dataset(name='tabmwp', split=split, cases=cases)


# ---------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------

class TabMWPEvaluator(Evaluator):
    """Compare predicted and expected answers for TabMWP.

    Handles numeric answers (integer and decimal) and text answers.
    """

    @staticmethod
    def _normalize(s: str) -> str:
        """Strip whitespace, currency symbols, percent signs, and units."""
        s = str(s).strip()
        # Remove leading currency symbols
        s = s.lstrip('$€£¥')
        # Remove trailing percent signs
        s = s.rstrip('%')
        return s.strip()

    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        predicted = self._normalize(predicted_output)
        expected = self._normalize(expected_output)

        # Try numeric comparison first
        try:
            pred_num = float(predicted.replace(',', ''))
            exp_num = float(expected.replace(',', ''))
            # Integer answers: exact match; decimal: tolerance
            if exp_num == int(exp_num):
                correct = abs(pred_num - exp_num) < 0.5
            else:
                correct = abs(pred_num - exp_num) < 0.01
            return dict(correct=correct)
        except (ValueError, OverflowError):
            pass

        # Text comparison: case-insensitive exact match
        correct = predicted.lower() == expected.lower()
        return dict(correct=correct)


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------

app = typer.Typer()

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}


def _setup(config_file: str, extra_args: list[str]) -> Dataset:
    """Shared setup: load config, populate table store, load dataset, implement ptools."""
    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path
    config.configure(yaml_file=str(cfg_path), dotlist=extra_args)
    config.set_root(_BENCHMARK_DIR)

    split = config.get('dataset.split', 'dev1k')

    # Populate table store for Option B tools
    raw_data = load_raw_data(split)
    ptools.load_table_store(raw_data)

    # Implement all ptools from config
    implement_via_config(ptools, config.require('ptools'))

    dataset = load_dataset(split).configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n'))
    print('dataset:', dataset.summary())
    return dataset


@app.command(context_settings=_EXTRA_ARGS)
def run(ctx: typer.Context,
        config_file: str = typer.Option(..., help="Config YAML file")):
    """Run TabMWP evaluation. Extra args are config overrides in dot notation."""
    dataset = _setup(config_file, ctx.args)

    entry_point = config.get('evaluate.entry_point', 'tabmwp_solve')
    interface = getattr(ptools, entry_point)

    evaluator = TabMWPEvaluator()
    csv_path = evaluator.evaluate(dataset, interface)
    df = pd.read_csv(csv_path)
    print(f'\nAccuracy: {df["correct"].mean():.1%} ({df["correct"].sum()}/{len(df)})')
    if 'cost' in df.columns:
        print(f'Avg cost: ${df["cost"].mean():.4f}/example')


@app.command(context_settings=_EXTRA_ARGS)
def quick_test(ctx: typer.Context,
               config_file: str = typer.Option(..., help="Config YAML file")):
    """Run a single example with verbose output for debugging."""
    dataset = _setup(config_file, ctx.args)
    print('dataset is', dataset.summary())
    pprint.pprint(config.GLOBAL_CONFIG)

    case = dataset.cases[0]
    print(f'\n--- Example {case.name} ---')
    print(f'Question: {case.input_args[0]}')
    print(f'Table:\n{case.input_args[1]}')
    print(f'Choices: {case.input_args[3]}')
    print(f'Expected: {case.expected_output}')

    entry_point = config.get('evaluate.entry_point', 'tabmwp_solve')
    interface = getattr(ptools, entry_point)

    with config.configuration(
            cachier={'enable_caching': False},
            echo={
                'service': True,
                'llm_input': True, 'llm_output': True,
                'code_eval_input': True, 'code_eval_output': True}
    ):
        with record.recorder() as records:
            predicted_output = interface(*case.input_args)
    print(f'\nPredicted: {predicted_output}')
    print(f'Expected:  {case.expected_output}')
    evaluator = TabMWPEvaluator()
    metrics = evaluator.compare_predictions(predicted_output, case.expected_output)
    print(f'Correct:   {metrics["correct"]}')
    print('\nRecords:')
    pprint.pprint(records)


if __name__ == '__main__':
    app()
