import warnings
from pathlib import Path
import pytest
import pandas as pd

pytestmark = pytest.mark.filterwarnings("ignore::RuntimeWarning")

from omegaconf import OmegaConf
from typer.testing import CliRunner

from secretagent import config
from secretagent.cli.results import (
    app, parse_metric, parse_metrics, paired_result_df, find_pareto_optimal,
    compute_hypervolume,
)


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
    d1 = _make_expt(tmp_path, '20260101.120000.baseline', 'baseline',
               {'llm': {'model': 'model-a'}},
               [{'correct': 1, 'latency': 1.0, 'cost': 0.01},
                {'correct': 0, 'latency': 2.0, 'cost': 0.02},
                {'correct': 1, 'latency': 1.5, 'cost': 0.015},
                {'correct': 1, 'latency': 1.2, 'cost': 0.012}])
    d2 = _make_expt(tmp_path, '20260102.120000.improved', 'improved',
               {'llm': {'model': 'model-b'}},
               [{'correct': 1, 'latency': 0.8, 'cost': 0.008},
                {'correct': 1, 'latency': 1.5, 'cost': 0.015},
                {'correct': 1, 'latency': 1.0, 'cost': 0.01},
                {'correct': 0, 'latency': 1.1, 'cost': 0.011}])
    return d1, d2


def _dirs_as_args(dirs):
    """Convert directory paths to CLI args."""
    return [str(d) for d in dirs]


# --- list tests ---

def test_list_shows_all(two_expts):
    result = runner.invoke(app, ['list', '--latest', '0'] + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'baseline' in result.output
    assert 'improved' in result.output
    assert '4' in result.output  # each has 4 rows


def test_list_filter_by_check(two_expts):
    result = runner.invoke(app, ['list', '--latest', '0',
                                  '--check', 'evaluate.expt_name=baseline']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'baseline' in result.output
    assert 'improved' not in result.output


def test_list_latest_default(two_expts):
    result = runner.invoke(app, ['list'] + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    # latest=1 means one per tag; these have different tags so both appear
    assert 'baseline' in result.output
    assert 'improved' in result.output


def test_list_no_results(tmp_path):
    # A nonexistent path raises ValueError (no config.yaml)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        result = runner.invoke(app, ['list', str(tmp_path / 'nonexistent')])
    assert result.exit_code != 0


def test_list_no_args():
    result = runner.invoke(app, ['list'])
    assert result.exit_code == 1


# --- average tests ---

def test_average_shows_metrics(two_expts):
    result = runner.invoke(app, ['average', '--latest', '0',
                                  '--metric', 'correct', '--metric', 'latency']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'mean' in result.output
    assert 'sem' in result.output


def test_average_single_expt(two_expts):
    result = runner.invoke(app, ['average', '--metric', 'correct',
                                  '--check', 'evaluate.expt_name=baseline']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    # only one experiment should appear (grouped by path)
    assert 'mean' in result.output


def test_average_shows_cost(two_expts):
    result = runner.invoke(app, ['average', '--latest', '0', '--metric', 'cost']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'cost' in result.output


# --- pair tests ---

def test_pair_runs(two_expts):
    result = runner.invoke(app, ['pair', '--latest', '0',
                                  '--metric', 'correct', '--metric', 'latency']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'latency_t' in result.output


def test_pair_needs_two_expts(two_expts):
    result = runner.invoke(app, ['pair', '--metric', 'correct',
                                  '--check', 'evaluate.expt_name=baseline']
                           + _dirs_as_args(two_expts))
    assert result.exit_code != 0


def test_pair_custom_metric(two_expts):
    result = runner.invoke(app, ['pair', '--latest', '0', '--metric', 'cost']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'cost' in result.output


# --- compare tests ---

def test_compare_configs_shows_diffs(two_expts):
    result = runner.invoke(app, ['compare-configs', '--latest', '0'] + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'properties of' in result.output
    assert 'llm.model=model-a' in result.output
    assert 'llm.model=model-b' in result.output


def test_compare_configs_single_expt(two_expts):
    result = runner.invoke(app, ['compare-configs', '--check', 'evaluate.expt_name=baseline']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0


# --- config file option ---

def test_config_file_option(two_expts, tmp_path):
    cfg_file = tmp_path / 'test_cfg.yaml'
    cfg_file.write_text(OmegaConf.to_yaml(OmegaConf.create(
        {'evaluate': {'result_dir': str(tmp_path)}})))
    # reset config so result_dir is not set
    config.GLOBAL_CONFIG = OmegaConf.create()
    result = runner.invoke(app, ['--config-file', str(cfg_file), 'list', '--latest', '0']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'baseline' in result.output


# --- parse_metric / parse_metrics tests ---

def test_parse_metric_maximize():
    assert parse_metric('correct') == ('correct', True)

def test_parse_metric_minimize():
    assert parse_metric('cost-') == ('cost', False)

def test_parse_metrics_mixed():
    names, directions = parse_metrics(['correct', 'cost-', 'latency-'])
    assert names == ['correct', 'cost', 'latency']
    assert directions == {'correct': True, 'cost': False, 'latency': False}


# --- paired_result_df tests ---

def test_paired_result_df_columns(two_expts):
    d1, d2 = two_expts
    dfs = [pd.read_csv(d / 'results.csv') for d in [d1, d2]]
    df = paired_result_df([d1, d2], dfs, ['correct', 'cost'])
    assert 'expt_a' in df.columns
    assert 'expt_b' in df.columns
    assert 'correct_t' in df.columns
    assert 'correct_p' in df.columns
    assert 'cost_t' in df.columns
    assert 'cost_p' in df.columns
    assert len(df) == 1  # one pair


def test_paired_result_df_zero_variance(tmp_path):
    """When a metric is identical across experiments, report t=0, p=1."""
    d1 = _make_expt(tmp_path, '20260101.120000.a', 'a',
                    {'llm': {'model': 'x'}},
                    [{'correct': 1, 'cost': 0.01},
                     {'correct': 1, 'cost': 0.01}])
    d2 = _make_expt(tmp_path, '20260102.120000.b', 'b',
                    {'llm': {'model': 'y'}},
                    [{'correct': 1, 'cost': 0.02},
                     {'correct': 1, 'cost': 0.02}])
    dfs = [pd.read_csv(d / 'results.csv') for d in [d1, d2]]
    df = paired_result_df([d1, d2], dfs, ['correct'])
    assert df.iloc[0]['correct_t'] == 0.0
    assert df.iloc[0]['correct_p'] == 1.0


# --- find_pareto_optimal tests ---

@pytest.fixture
def three_expts(tmp_path):
    """Three experiments with clear separations for significance.

    best:  correct=1.0, cost=0.01  (perfect, cheap)
    mid:   correct=0.5, cost=0.50  (middling)
    worst: correct=0.0, cost=1.00  (bad, expensive)
    Using 8 samples with no variance so t-tests are clearly significant.
    """
    best = _make_expt(tmp_path, '20260101.120000.best', 'best',
                      {'llm': {'model': 'a'}},
                      [{'correct': 1, 'cost': 0.01}] * 8)
    mid = _make_expt(tmp_path, '20260102.120000.mid', 'mid',
                     {'llm': {'model': 'b'}},
                     [{'correct': 1, 'cost': 0.50}] * 4
                     + [{'correct': 0, 'cost': 0.50}] * 4)
    worst = _make_expt(tmp_path, '20260103.120000.worst', 'worst',
                       {'llm': {'model': 'c'}},
                       [{'correct': 0, 'cost': 1.00}] * 8)
    return best, mid, worst


def test_find_pareto_all_maximize(three_expts):
    """With both metrics maximized, worst has highest cost so nobody dominates it."""
    dirs = list(three_expts)
    dfs = [pd.read_csv(d / 'results.csv') for d in dirs]
    pair_df = paired_result_df(dirs, dfs, ['correct', 'cost'])
    optimal = find_pareto_optimal(pair_df, ['correct', 'cost'])
    assert len(optimal) == 3


def test_find_pareto_with_minimize(three_expts):
    """With correct maximized and cost minimized, best dominates others."""
    dirs = list(three_expts)
    dfs = [pd.read_csv(d / 'results.csv') for d in dirs]
    pair_df = paired_result_df(dirs, dfs, ['correct', 'cost'])
    directions = {'correct': True, 'cost': False}
    optimal = find_pareto_optimal(pair_df, ['correct', 'cost'], directions=directions)
    assert 'best' in optimal
    assert 'worst' not in optimal


def test_find_pareto_tradeoff(tmp_path):
    """Two experiments with a tradeoff: neither dominates the other."""
    accurate = _make_expt(tmp_path, '20260101.120000.accurate', 'accurate',
                          {'llm': {'model': 'a'}},
                          [{'correct': 1, 'cost': 0.10},
                           {'correct': 1, 'cost': 0.10},
                           {'correct': 1, 'cost': 0.10},
                           {'correct': 1, 'cost': 0.10}])
    cheap = _make_expt(tmp_path, '20260102.120000.cheap', 'cheap',
                       {'llm': {'model': 'b'}},
                       [{'correct': 0, 'cost': 0.001},
                        {'correct': 0, 'cost': 0.001},
                        {'correct': 0, 'cost': 0.001},
                        {'correct': 1, 'cost': 0.001}])
    dirs = [accurate, cheap]
    dfs = [pd.read_csv(d / 'results.csv') for d in dirs]
    pair_df = paired_result_df(dirs, dfs, ['correct', 'cost'])
    directions = {'correct': True, 'cost': False}
    optimal = find_pareto_optimal(pair_df, ['correct', 'cost'], directions=directions)
    assert 'accurate' in optimal
    assert 'cheap' in optimal


# --- average --pareto tests ---

def test_average_pareto_flag(three_expts):
    result = runner.invoke(app, ['average', '--latest', '0', '--pareto',
                                  '--metric', 'correct', '--metric', 'cost-']
                           + _dirs_as_args(three_expts))
    assert result.exit_code == 0
    # Only best (correct=1.0, cost=0.01) should survive pareto filtering.
    # worst (correct=0.0, cost=1.0) should be eliminated.
    lines = result.output.strip().split('\n')
    # Header lines + 1 data row (best only)
    data_lines = [l for l in lines if '0.' in l and 'mean' not in l and 'sem' not in l]
    assert len(data_lines) == 1
    assert '0.01' in data_lines[0]  # best's cost


# --- pair with minimize suffix ---

def test_pair_strips_suffix(two_expts):
    result = runner.invoke(app, ['pair', '--latest', '0', '--metric', 'cost-']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'cost_t' in result.output


# --- plot tests ---

def test_plot_creates_png(two_expts, tmp_path):
    out = str(tmp_path / 'test_plot.png')
    result = runner.invoke(app, ['plot', '--latest', '0',
                                  '--metric', 'correct', '--metric', 'cost-',
                                  '--output', out]
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_plot_requires_two_metrics(two_expts, tmp_path):
    out = str(tmp_path / 'bad.png')
    result = runner.invoke(app, ['plot', '--latest', '0',
                                  '--metric', 'correct',
                                  '--output', out]
                           + _dirs_as_args(two_expts))
    assert result.exit_code != 0


def test_plot_with_pareto(three_expts, tmp_path):
    out = str(tmp_path / 'pareto_plot.png')
    result = runner.invoke(app, ['plot', '--latest', '0', '--pareto',
                                  '--metric', 'correct', '--metric', 'cost-',
                                  '--output', out]
                           + _dirs_as_args(three_expts))
    assert result.exit_code == 0
    assert Path(out).exists()


# --- export tests ---

def test_export_copies_dirs(tmp_path, monkeypatch):
    """Export copies filtered result dirs to paper/results/results/<rel_path>."""
    bench_dir = tmp_path / 'benchmarks' / 'mybench'
    bench_dir.mkdir(parents=True)
    d1 = _make_expt(bench_dir, 'results/20260101.120000.alpha', 'alpha',
                    {'llm': {'model': 'a'}},
                    [{'correct': 1, 'cost': 0.01}])
    d2 = _make_expt(bench_dir, 'results/20260102.120000.beta', 'beta',
                    {'llm': {'model': 'b'}},
                    [{'correct': 0, 'cost': 0.02}])
    monkeypatch.chdir(bench_dir)
    result = runner.invoke(app, ['export', '--latest', '0']
                           + _dirs_as_args([d1, d2]))
    assert result.exit_code == 0
    export_base = tmp_path / 'paper' / 'results' / 'results' / 'mybench'
    assert (export_base / '20260101.120000.alpha' / 'results.csv').exists()
    assert (export_base / '20260102.120000.beta' / 'results.csv').exists()


def test_export_skips_existing(tmp_path, monkeypatch):
    """Export skips directories that already exist at the destination."""
    bench_dir = tmp_path / 'benchmarks' / 'mybench'
    bench_dir.mkdir(parents=True)
    d1 = _make_expt(bench_dir, 'results/20260101.120000.alpha', 'alpha',
                    {'llm': {'model': 'a'}},
                    [{'correct': 1, 'cost': 0.01}])
    dest = tmp_path / 'paper' / 'results' / 'results' / 'mybench' / '20260101.120000.alpha'
    dest.mkdir(parents=True)
    monkeypatch.chdir(bench_dir)
    result = runner.invoke(app, ['export', '--latest', '0'] + _dirs_as_args([d1]))
    assert result.exit_code == 0
    assert 'skipping' in result.output


def test_export_as_path(tmp_path, monkeypatch):
    """--as overrides the relative path under paper/results/results/."""
    bench_dir = tmp_path / 'benchmarks' / 'mybench'
    bench_dir.mkdir(parents=True)
    d1 = _make_expt(bench_dir, 'results/20260101.120000.alpha', 'alpha',
                    {'llm': {'model': 'a'}},
                    [{'correct': 1, 'cost': 0.01}])
    monkeypatch.chdir(bench_dir)
    result = runner.invoke(app, ['export', '--latest', '0',
                                  '--as', 'custom/path']
                           + _dirs_as_args([d1]))
    assert result.exit_code == 0
    export_dest = tmp_path / 'paper' / 'results' / 'results' / 'custom' / 'path'
    assert (export_dest / '20260101.120000.alpha' / 'results.csv').exists()


# --- compute_hypervolume unit tests ---

def test_hypervolume_2d_single_point():
    """Single point above reference."""
    hv = compute_hypervolume([[3.0, 4.0]], [1.0, 2.0])
    assert hv == pytest.approx(4.0)  # (3-1) * (4-2)


def test_hypervolume_2d_two_points():
    """Two non-dominated points forming an L-shape."""
    # Points: (4, 2) and (2, 4), ref: (0, 0)
    # Area = 4*4 + 2*2 - 2*2 = 16+4-4 = ... let's compute manually
    # Sort by x desc: (4,2), (2,4)
    # sweep: x=4,y=2: vol += (4-0)*(2-0) = 8, y_max=2
    #        x=2,y=4: vol += (2-0)*(4-2) = 4, y_max=4
    # total = 12
    hv = compute_hypervolume([[4.0, 2.0], [2.0, 4.0]], [0.0, 0.0])
    assert hv == pytest.approx(12.0)


def test_hypervolume_dominated_point_no_effect():
    """Adding a dominated point doesn't change hypervolume."""
    points_without = [[4.0, 4.0]]
    points_with = [[4.0, 4.0], [2.0, 2.0]]
    ref = [0.0, 0.0]
    assert compute_hypervolume(points_without, ref) == compute_hypervolume(points_with, ref)


def test_hypervolume_point_at_ref():
    """A point equal to the reference contributes nothing."""
    hv = compute_hypervolume([[1.0, 1.0]], [1.0, 1.0])
    assert hv == pytest.approx(0.0)


def test_hypervolume_1d():
    hv = compute_hypervolume([[5.0], [3.0]], [1.0])
    assert hv == pytest.approx(4.0)  # max(5,3) - 1


def test_hypervolume_3d():
    """Basic 3D hypervolume with a single point."""
    hv = compute_hypervolume([[3.0, 4.0, 5.0]], [1.0, 2.0, 3.0])
    assert hv == pytest.approx(2.0 * 2.0 * 2.0)  # 8.0


# --- hypervolume CLI tests ---

def test_hypervolume_cli_runs(two_expts):
    result = runner.invoke(app, ['hypervolume', '--latest', '0',
                                  '--metric', 'correct', '--metric', 'cost-']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'Hypervolume:' in result.output


def test_hypervolume_cli_with_ref(two_expts):
    result = runner.invoke(app, ['hypervolume', '--latest', '0',
                                  '--metric', 'correct', '--metric', 'cost-',
                                  '--ref', '0.0,0.0']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'Hypervolume:' in result.output


def test_hypervolume_cli_bad_ref(two_expts):
    result = runner.invoke(app, ['hypervolume', '--latest', '0',
                                  '--metric', 'correct', '--metric', 'cost-',
                                  '--ref', '0.0']
                           + _dirs_as_args(two_expts))
    assert result.exit_code != 0


def test_hypervolume_cli_defaults(two_expts):
    """Default metrics are cost- and correct."""
    result = runner.invoke(app, ['hypervolume', '--latest', '0']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    assert 'cost-' in result.output
    assert 'correct' in result.output


# --- refpoint CLI tests ---

def test_refpoint_cli_runs(two_expts):
    result = runner.invoke(app, ['refpoint', '--latest', '0',
                                  '--metric', 'correct', '--metric', 'cost-']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
    # Output should be comma-separated floats
    line = result.output.strip().split('\n')[0]
    parts = line.split(',')
    assert len(parts) == 2
    for p in parts:
        float(p)  # should not raise


def test_refpoint_cli_defaults(two_expts):
    result = runner.invoke(app, ['refpoint', '--latest', '0']
                           + _dirs_as_args(two_expts))
    assert result.exit_code == 0
