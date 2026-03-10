"""Tests for secretagent.evaluate."""

import os
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
    def measure(self, example: Case, iface) -> dict[str, Any]:
        output = iface(*example.input_args)
        return dict(
            name=example.name,
            output=output,
            correct=(output == example.expected_output),
            stats={'cost': 0.01, 'latency': 0.1},
        )


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

def test_evaluate_returns_results():
    ev = DummyEvaluator()
    ds = _make_dataset(3)
    results = ev.evaluate(ds, times_ten)
    assert len(results) == 3
    for r in results:
        assert r['correct']
        assert r['expt_name'] == '**unnamed_expt**'


def test_evaluate_uses_expt_name():
    config.configure(evaluate={'expt_name': 'my_expt'})
    ev = DummyEvaluator()
    ds = _make_dataset(2)
    results = ev.evaluate(ds, times_ten)
    assert all(r['expt_name'] == 'my_expt' for r in results)


def test_evaluate_saves_results(tmp_path):
    config.configure(evaluate={'expt_name': 'save_test', 'result_dir': str(tmp_path)})
    ev = DummyEvaluator()
    ds = _make_dataset(2)
    ev.evaluate(ds, times_ten)

    # should have created a timestamped subdirectory
    subdirs = list(tmp_path.iterdir())
    assert len(subdirs) == 1
    result_dir = subdirs[0]
    assert 'save_test' in result_dir.name
    assert (result_dir / 'results.csv').exists()
    assert (result_dir / 'config.yaml').exists()
