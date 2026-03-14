import json
import pytest
import pandas as pd
from pathlib import Path

from omegaconf import OmegaConf
from typer.testing import CliRunner

from secretagent import config
from secretagent.cli.results import app


runner = CliRunner()


@pytest.fixture(autouse=True)
def clean_config():
    saved = config.GLOBAL_CONFIG.copy()
    yield
    config.GLOBAL_CONFIG = saved


def _make_expt(base, dirname, expt_name, cfg_dict, rows):
    """Create a fake experiment directory with config.yaml and results.csv."""
    d = base / dirname
    d.mkdir(parents=True, exist_ok=True)
    # write config
    full_cfg = {**cfg_dict, 'evaluate': {'expt_name': expt_name, 'result_dir': str(base)}}
    with open(d / 'config.yaml', 'w') as f:
        f.write(OmegaConf.to_yaml(OmegaConf.create(full_cfg)))
    # write results.csv
    df = pd.DataFrame(rows)
    df['expt_name'] = expt_name
    df.to_csv(d / 'results.csv', index=False)
    return d


@pytest.fixture
def two_expts(tmp_path):
    """Create two experiment directories with different configs and results."""
    config.configure(evaluate={'result_dir': str(tmp_path)})
    _make_expt(tmp_path, '20260101.120000.baseline', 'baseline',
               {'llm': {'model': 'model-a'}},
               [{'correct': 1, 'latency': 1.0, 'cost': 0.01},
                {'correct': 0, 'latency': 2.0, 'cost': 0.02},
                {'correct': 1, 'latency': 1.5, 'cost': 0.015},
                {'correct': 1, 'latency': 1.2, 'cost': 0.012}])
    _make_expt(tmp_path, '20260102.120000.improved', 'improved',
               {'llm': {'model': 'model-b'}},
               [{'correct': 1, 'latency': 0.8, 'cost': 0.008},
                {'correct': 1, 'latency': 1.5, 'cost': 0.015},
                {'correct': 1, 'latency': 1.0, 'cost': 0.01},
                {'correct': 0, 'latency': 1.1, 'cost': 0.011}])
    return tmp_path


# --- list tests ---

def test_list_shows_all(two_expts):
    result = runner.invoke(app, ['list'])
    assert result.exit_code == 0
    assert 'baseline' in result.output
    assert 'improved' in result.output
    assert '4' in result.output  # each has 4 rows


def test_list_filter_by_expt(two_expts):
    result = runner.invoke(app, ['list', '--expt', 'baseline'])
    assert result.exit_code == 0
    assert 'baseline' in result.output
    assert 'improved' not in result.output


def test_list_most_recent(two_expts):
    result = runner.invoke(app, ['list', '--most-recent'])
    assert result.exit_code == 0
    assert 'improved' in result.output
    # only one line with a count
    lines = [l for l in result.output.strip().split('\n') if l.strip()]
    assert len(lines) == 1


def test_list_no_results(tmp_path):
    config.configure(evaluate={'result_dir': str(tmp_path)})
    result = runner.invoke(app, ['list'])
    assert result.exit_code == 1
    assert 'No matching' in result.output


# --- average tests ---

def test_average_shows_metrics(two_expts):
    result = runner.invoke(app, ['average'])
    assert result.exit_code == 0
    assert 'baseline' in result.output
    assert 'improved' in result.output
    assert '+/-' in result.output


def test_average_single_expt(two_expts):
    result = runner.invoke(app, ['average', '--expt', 'baseline'])
    assert result.exit_code == 0
    assert 'baseline' in result.output
    assert 'improved' not in result.output


def test_average_shows_cost(two_expts):
    result = runner.invoke(app, ['average'])
    assert result.exit_code == 0
    assert '$' in result.output


# --- pair tests ---

def test_pair_runs(two_expts):
    result = runner.invoke(app, ['pair'])
    assert result.exit_code == 0
    assert 'baseline' in result.output
    assert 'improved' in result.output
    assert 'correct' in result.output
    assert 'latency' in result.output
    assert 'p=' in result.output


def test_pair_needs_two_expts(two_expts):
    result = runner.invoke(app, ['pair', '--expt', 'baseline'])
    assert result.exit_code == 1
    assert 'Need at least 2' in result.output


def test_pair_custom_metric(two_expts):
    result = runner.invoke(app, ['pair', '--metric', 'cost'])
    assert result.exit_code == 0
    assert 'cost' in result.output


# --- compare tests ---

def test_compare_shows_diffs(two_expts):
    result = runner.invoke(app, ['compare'])
    assert result.exit_code == 0
    assert 'llm.model' in result.output
    assert 'model-a' in result.output
    assert 'model-b' in result.output


def test_compare_needs_two(two_expts):
    result = runner.invoke(app, ['compare', '--expt', 'baseline'])
    assert result.exit_code == 1
    assert 'Need at least 2' in result.output


# --- config file option ---

def test_config_file_option(two_expts, tmp_path):
    cfg_file = tmp_path / 'test_cfg.yaml'
    cfg_file.write_text(OmegaConf.to_yaml(OmegaConf.create(
        {'evaluate': {'result_dir': str(tmp_path)}})))
    # reset config so result_dir is not set
    config.GLOBAL_CONFIG = OmegaConf.create()
    result = runner.invoke(app, ['--config-file', str(cfg_file), 'list'])
    assert result.exit_code == 0
    assert 'baseline' in result.output
