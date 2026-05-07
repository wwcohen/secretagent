"""Tests for secretagent.cli.expt — config isolation."""

from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from omegaconf import OmegaConf

from secretagent import config
from secretagent.cli.expt import run_experiment


@pytest.fixture(autouse=True)
def reset_global_config():
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


def _fake_setup(dotlist):
    """Simulate setup_and_load_dataset: mutates config and returns a dataset."""
    config.configure(llm={'model': 'mutated-model'}, echo={'call': True})
    ds = MagicMock()
    return ds


def test_run_experiment_does_not_leak_config():
    """run_experiment should not permanently change GLOBAL_CONFIG."""
    config.configure(llm={'model': 'original'})

    csv_path = '/tmp/fake_results.csv'
    fake_df = pd.DataFrame({'correct': [1, 0, 1]})
    fake_evaluator = MagicMock()
    fake_evaluator.evaluate.return_value = csv_path

    with patch('secretagent.cli.expt.setup_and_load_dataset', side_effect=_fake_setup), \
         patch('pandas.read_csv', return_value=fake_df):
        run_experiment(
            top_level_interface=MagicMock(),
            dotlist=['echo.model=True'],
            evaluator=fake_evaluator,
        )

    assert config.get('llm.model') == 'original'
    assert config.get('echo.call') is None
    assert config.get('echo.model') is None
