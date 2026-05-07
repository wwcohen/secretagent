"""Tests for secretagent.evaluate."""

import pytest
from omegaconf import OmegaConf
from typing import Any

from secretagent import config
from secretagent.dataset import Case, Dataset
from secretagent.core import interface
from secretagent.evaluate import Evaluator


@pytest.fixture(autouse=True)
def reset_config():
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


def _make_dataset(n=3):
    return Dataset(
        name='test',
        cases=[Case(name=f'case_{i}', input_args=[i], expected_output=i * 10) for i in range(n)],
    )


class DummyEvaluator(Evaluator):
    """Simple evaluator that calls the interface and checks correctness."""
    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        return dict(correct=(predicted_output == expected_output))


@interface
def times_ten(x: int) -> int:
    """Multiply x by 10."""
    return x * 10

times_ten.implement_via('direct')


# --- aggregate_usage_stats ---

def test_aggregate_usage_stats():
    ev = DummyEvaluator()
    records = [
        {'stats': {'cost': 0.01, 'latency': 0.5}},
        {'stats': {'cost': 0.02, 'latency': 0.3}},
    ]
    totals = ev.aggregate_usage_stats(records)
    assert abs(totals['cost'] - 0.03) < 1e-9
    assert abs(totals['latency'] - 0.8) < 1e-9


# --- evaluate ---

def test_evaluate_returns_csv_path(tmp_path):
    config.configure(evaluate={'result_dir': str(tmp_path)})
    ev = DummyEvaluator()
    ds = _make_dataset(3)
    csv_path = ev.evaluate(ds, times_ten)
    assert csv_path.name == 'results.csv'
    assert csv_path.exists()
    # read back and verify contents
    import pandas as pd
    df = pd.read_csv(csv_path, index_col='case_name')
    assert len(df) == 3
    assert all(df['correct'])
    assert list(df.index) == ['case_0', 'case_1', 'case_2']


def test_evaluate_uses_expt_name(tmp_path):
    config.configure(evaluate={'expt_name': 'my_expt', 'result_dir': str(tmp_path)})
    ev = DummyEvaluator()
    ds = _make_dataset(2)
    csv_path = ev.evaluate(ds, times_ten)
    assert 'my_expt' in csv_path.parent.name
    import json
    jsonl_path = csv_path.parent / 'results.jsonl'
    rows = [json.loads(line) for line in jsonl_path.read_text().splitlines()]
    assert all(r['expt_name'] == 'my_expt' for r in rows)


def test_evaluate_saves_results(tmp_path):
    config.configure(evaluate={'expt_name': 'save_test', 'result_dir': str(tmp_path)})
    ev = DummyEvaluator()
    ds = _make_dataset(2)
    csv_path = ev.evaluate(ds, times_ten)

    # returned path should be inside a timestamped subdirectory
    result_dir = csv_path.parent
    assert 'save_test' in result_dir.name
    assert csv_path.exists()
    assert (result_dir / 'results.jsonl').exists()
    assert (result_dir / 'config.yaml').exists()
