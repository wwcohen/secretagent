"""CLI for analyzing experiment results saved by savefile.

Commands:
    list      Show available experiments and number of examples
    average   Report mean +/- stderr of metrics grouped by experiment.
    pair      Run paired t-tests on metrics across experiments.
    compare   Show configuration differences between experiments.

Experiments are found via savefile.getfiles(), which scans the
directory specified by the 'evaluate.result_dir' config key.

Example usage:

    # List all experiments
    uv run -m secretagent.cli.results list

    # List only experiments tagged 'baseline'
    uv run -m secretagent.cli.results list --expt baseline

    # Show averages for the two most recent experiments
    uv run -m secretagent.cli.results average --most-recent

    # Paired t-test between experiments with different models
    uv run -m secretagent.cli.results pair

    # Compare configs across experiments
    uv run -m secretagent.cli.results compare
"""

import typer
import pandas as pd
from itertools import combinations
from pathlib import Path
from typing import Optional

from omegaconf import OmegaConf
from scipy import stats as scipy_stats

from secretagent import config, savefile

app = typer.Typer()

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}


def _apply_dotlist(ctx: typer.Context):
    """Apply any dotlist config overrides from extra CLI args."""
    if ctx.args:
        config.configure(dotlist=ctx.args)


def _get_dirs(
    expt: Optional[str],
    most_recent: bool,
) -> list[Path]:
    """Find experiment directories, optionally filtering by expt_name."""
    basedir = config.require('evaluate.result_dir')
    dirs = savefile.getfiles(basedir, file_under=expt, most_recent=most_recent)
    if not dirs:
        typer.echo('No matching experiment directories found.')
        raise typer.Exit(1)
    return dirs


def _load_csv(dirs: list[Path]) -> pd.DataFrame:
    """Load and concatenate results.csv from each experiment directory."""
    frames = []
    for d in dirs:
        csv_path = d / 'results.csv'
        if csv_path.exists():
            frames.append(pd.read_csv(csv_path))
    if not frames:
        typer.echo('No results.csv files found.')
        raise typer.Exit(1)
    return pd.concat(frames, ignore_index=True)


def _load_config(d: Path) -> dict:
    """Load config.yaml from an experiment directory."""
    cfg_path = d / 'config.yaml'
    if not cfg_path.exists():
        return {}
    return OmegaConf.to_container(OmegaConf.load(cfg_path), resolve=True)


def _flatten(d, prefix=''):
    """Flatten a nested dict into dot-separated keys."""
    items = {}
    for k, v in d.items():
        key = f'{prefix}.{k}' if prefix else k
        if isinstance(v, dict):
            items.update(_flatten(v, key))
        else:
            items[key] = v
    return items


@app.command('list', context_settings=_EXTRA_ARGS)
def list_experiments(
    ctx: typer.Context,
    expt: Optional[str] = typer.Option(None, help='Filter by expt_name'),
    most_recent: bool = typer.Option(True, help='Only show most recent; use --no-most-recent for all'),
):
    """Show available experiment directories and row counts."""
    _apply_dotlist(ctx)
    basedir = config.require('evaluate.result_dir')
    dirs = savefile.getfiles(basedir, file_under=expt, most_recent=most_recent)
    if not dirs:
        typer.echo('No matching experiment directories found.')
        raise typer.Exit(1)
    for d in dirs:
        csv_path = d / 'results.csv'
        if csv_path.exists():
            n = len(pd.read_csv(csv_path))
            typer.echo(f'{n:5d}  {d.name}')
        else:
            typer.echo(f'    ?  {d.name}  (no results.csv)')


@app.command(context_settings=_EXTRA_ARGS)
def average(
    ctx: typer.Context,
    expt: Optional[str] = typer.Option(None, help='Filter by expt_name'),
    most_recent: bool = typer.Option(True, help='Only show most recent; use --no-most-recent for all'),
    metric: str = typer.Option('correct', help='Metric column to summarize'),
):
    """Report mean +/- stderr of a metric and latency, grouped by experiment."""
    _apply_dotlist(ctx)
    dirs = _get_dirs(expt, most_recent)
    df = _load_csv(dirs)
    stats = df.groupby('expt_name').agg(
        n=(metric, 'count'),
        metric_mean=(metric, 'mean'),
        metric_sem=(metric, 'sem'),
        latency_mean=('latency', 'mean'),
        latency_sem=('latency', 'sem'),
        cost_sum=('cost', 'sum'),
    )
    stats[metric] = stats.apply(
        lambda r: f'{r.metric_mean:.3f} +/- {r.metric_sem:.3f}', axis=1)
    stats['latency'] = stats.apply(
        lambda r: f'{r.latency_mean:.3f} +/- {r.latency_sem:.3f}', axis=1)
    stats['cost'] = stats['cost_sum'].apply(lambda c: f'${c:.4f}')
    typer.echo(stats[['n', metric, 'latency', 'cost']].to_string())


@app.command(context_settings=_EXTRA_ARGS)
def pair(
    ctx: typer.Context,
    expt: Optional[str] = typer.Option(None, help='Filter by expt_name'),
    most_recent: bool = typer.Option(True, help='Only show most recent; use --no-most-recent for all'),
    metric: str = typer.Option('correct', help='Metric column to compare'),
):
    """Run paired t-tests on a metric and latency across experiments."""
    _apply_dotlist(ctx)
    dirs = _get_dirs(expt, most_recent)
    df = _load_csv(dirs)
    experiments = sorted(df['expt_name'].unique())
    if len(experiments) < 2:
        typer.echo('Need at least 2 experiments for paired comparison.')
        raise typer.Exit(1)
    # group by experiment; use row index within each group for pairing
    by_expt = {}
    for name, group in df.groupby('expt_name'):
        by_expt[name] = group.reset_index(drop=True)
    for a, b in combinations(experiments, 2):
        da, db = by_expt[a], by_expt[b]
        n = min(len(da), len(db))
        if n < 2:
            typer.echo(f'\n{a} vs {b}: not enough rows (n={n}), skipping')
            continue
        da, db = da.iloc[:n], db.iloc[:n]
        met_t, met_p = scipy_stats.ttest_rel(da[metric], db[metric])
        lat_t, lat_p = scipy_stats.ttest_rel(da['latency'], db['latency'])
        typer.echo(f'\n{a} vs {b}  (n={n} paired examples)')
        typer.echo(f'  {metric}:  t={met_t:+.3f}  p={met_p:.4f}{"  *" if met_p < 0.05 else ""}')
        typer.echo(f'  latency:  t={lat_t:+.3f}  p={lat_p:.4f}{"  *" if lat_p < 0.05 else ""}')


@app.command(context_settings=_EXTRA_ARGS)
def compare(
    ctx: typer.Context,
    expt: Optional[str] = typer.Option(None, help='Filter by expt_name'),
    most_recent: bool = typer.Option(True, help='Only show most recent; use --no-most-recent for all'),
):
    """Show configuration differences between experiments."""
    _apply_dotlist(ctx)
    dirs = _get_dirs(expt, most_recent)
    if len(dirs) < 2:
        typer.echo('Need at least 2 experiment directories to compare.')
        raise typer.Exit(1)
    configs = {}
    for d in dirs:
        cfg = _load_config(d)
        if cfg:
            configs[d.name] = _flatten(cfg)
    if len(configs) < 2:
        typer.echo('Not enough configs found to compare.')
        raise typer.Exit(1)
    names = list(configs.keys())
    all_keys = sorted(set().union(*(c.keys() for c in configs.values())))
    diffs = []
    for key in all_keys:
        values = [configs[n].get(key) for n in names]
        if len(set(str(v) for v in values)) > 1:
            diffs.append((key, values))
    if not diffs:
        typer.echo('All configurations are identical.')
        return
    typer.echo('Configuration differences:\n')
    col_width = max(len(n) for n in names)
    header = '  '.join(f'{n:>{col_width}}' for n in names)
    typer.echo(f"{'key':<30}  {header}")
    typer.echo('-' * (30 + 2 + (col_width + 2) * len(names)))
    for key, values in diffs:
        vals = '  '.join(f'{str(v):>{col_width}}' for v in values)
        typer.echo(f'{key:<30}  {vals}')


@app.callback()
def main(
    config_file: Optional[str] = typer.Option(None, help='YAML config file to load'),
):
    """Analyze experiment results saved by savefile.

    Extra args after the subcommand are parsed as config overrides in
    dot notation, e.g.:
        uv run -m secretagent.cli.results list evaluate.result_dir=/tmp/results
    """
    if config_file:
        config.configure(yaml_file=config_file)


if __name__ == '__main__':
    app()
