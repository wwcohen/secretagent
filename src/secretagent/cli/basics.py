"""Repo-root runner for the "basics" strategy grid.

Reproduces the per-task ``make basics`` targets, but driven from the repo
root instead of cd-ing into each benchmark directory. It discovers a
per-task ``strategies.yaml`` manifest under ``benchmarks/`` (so the
strategy config lives in the benchmark dirs, not in this code), then runs
each ``model x task x strategy`` cell via ``secretagent.cli.expt run`` as a
subprocess.

Results land under ``overall_results/<model>/<task>/<strategy>/`` at the
repo root -- nothing is written into the benchmark/task dirs. Each task's
own LLM cache (the absolute ``cachier.cache_dir`` baked into its conf) is
reused, so reruns are cheap.

A manifest looks like::

    config: conf/conf.yaml              # relative to the task dir
    evaluator: evaluator.TripEvaluator  # dotted; omit/null for ExactMatch
    strategies:
      structured_baseline:
        - ptools.trip_planning.method=simulate
      workflow:
        - ptools.trip_planning.method=direct
        - ptools.trip_planning.fn=ptools.trip_workflow

Usage::

    uv run python -m secretagent.cli.basics list
    uv run python -m secretagent.cli.basics run --dry-run
    uv run python -m secretagent.cli.basics run --n 10 --strategies structured_baseline
    uv run python -m secretagent.cli.basics run --models gemini/gemini-3.1-pro
"""

import os
import subprocess
from pathlib import Path

import pandas as pd
import typer
import yaml

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}
app = typer.Typer(pretty_exceptions_enable=False)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_BENCH_ROOT = _PROJECT_ROOT / 'benchmarks'
_DEFAULT_OUT = _PROJECT_ROOT / 'overall_results'

# best/newest and cheapest gemini, per PERSONAL_TODO 3. Override with --models.
# NB: the 3.1-pro tier resolves only under the -preview id; bare
# gemini/gemini-3.1-pro returns a litellm 404 (verified 2026-06-18).
_DEFAULT_MODELS = ['gemini/gemini-3.1-pro-preview', 'gemini/gemini-2.5-flash-lite']


class Task:
    """A discovered benchmark task and its strategy manifest."""

    def __init__(self, manifest_path: Path):
        self.dir = manifest_path.parent
        self.id = self.dir.relative_to(_BENCH_ROOT).as_posix()
        spec = yaml.safe_load(manifest_path.read_text(encoding='utf-8'))
        self.config = self.dir / spec.get('config', 'conf/conf.yaml')
        self.evaluator = spec.get('evaluator')
        self.strategies = spec['strategies']


def _discover(task_filter: list[str] | None) -> list[Task]:
    """Find every benchmarks/**/strategies.yaml, optionally filtered by id."""
    tasks = [Task(p) for p in sorted(_BENCH_ROOT.glob('**/strategies.yaml'))]
    if task_filter:
        wanted = set(task_filter)
        tasks = [t for t in tasks if t.id in wanted]
    return tasks


def _model_slug(model: str) -> str:
    return model.replace('/', '_')


def _build_command(task: Task, strategy: str, model: str, result_dir: Path,
                   n: int | None, extra: list[str]) -> list[str]:
    """Assemble the `expt run` subprocess argv for one grid cell."""
    cmd = ['uv', 'run', 'python', '-m', 'secretagent.cli.expt', 'run',
           '--config', str(task.config)]
    if task.evaluator:
        cmd += ['--evaluator', task.evaluator]
    cmd += list(task.strategies[strategy])
    cmd += [
        f'evaluate.expt_name={strategy}',
        f'llm.model={model}',
        f'evaluate.result_dir={result_dir}',
    ]
    if n:
        cmd.append(f'dataset.n={n}')
    cmd += extra  # user overrides win (placed last)
    return cmd


def _latest_metrics(result_dir: Path) -> dict:
    """Mean of numeric columns from the newest results.csv under result_dir.

    Includes bool columns (mean -> fraction True): the default
    ExactMatchEvaluator writes `correct` as 0/1 (int), but the natural_plan
    evaluators write True/False (bool), which a number-only filter would drop.
    """
    csvs = sorted(result_dir.glob('*/results.csv'))
    if not csvs:
        return {}
    df = pd.read_csv(csvs[-1])
    return df.select_dtypes(include=['number', 'bool']).mean().to_dict()


@app.command('list')
def list_tasks():
    """List discovered tasks and their strategies."""
    tasks = _discover(None)
    print(f'{"Task":<34} Strategies')
    print('-' * 70)
    for t in tasks:
        ev = f'  (evaluator: {t.evaluator})' if t.evaluator else ''
        print(f'{t.id:<34} {", ".join(t.strategies)}{ev}')
    print(f'\n{len(tasks)} tasks under {_BENCH_ROOT}')


@app.command(context_settings=_EXTRA_ARGS)
def run(
    ctx: typer.Context,
    models: str = typer.Option(','.join(_DEFAULT_MODELS), '--models',
                               help='Comma-separated llm.model values'),
    tasks: str = typer.Option(None, '--tasks',
                              help='Comma-separated task ids (default: all discovered)'),
    strategies: str = typer.Option(None, '--strategies',
                                   help='Comma-separated strategy names (default: all in each manifest)'),
    n: int = typer.Option(None, '--n', help='dataset.n (minibatch); default: full pool'),
    out: str = typer.Option(str(_DEFAULT_OUT), '--out', help='Output root for results'),
    dry_run: bool = typer.Option(False, '--dry-run', help='Print commands without running'),
):
    """Run the model x task x strategy grid from the repo root.

    Extra positional args are passed as dotlist overrides to every cell.
    """
    model_list = [m.strip() for m in models.split(',') if m.strip()]
    task_filter = [t.strip() for t in tasks.split(',')] if tasks else None
    strat_filter = {s.strip() for s in strategies.split(',')} if strategies else None
    out_root = Path(out)
    discovered = _discover(task_filter)
    if not discovered:
        print('No tasks discovered (no benchmarks/**/strategies.yaml).')
        raise typer.Exit(1)

    rows = []
    for model in model_list:
        for task in discovered:
            names = [s for s in task.strategies if not strat_filter or s in strat_filter]
            for strategy in names:
                result_dir = out_root / _model_slug(model) / task.id / strategy
                cmd = _build_command(task, strategy, model, result_dir, n, ctx.args)
                print(f'\n{"="*70}\n  {model}  {task.id}  {strategy}\n  {" ".join(cmd)}\n{"="*70}')
                if dry_run:
                    continue
                result_dir.mkdir(parents=True, exist_ok=True)
                # Run each cell in Python UTF-8 mode so LLM output with
                # non-cp1252 chars doesn't crash on Windows ('charmap' codec
                # can't encode ...). Affects both stdio and open() defaults.
                env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
                rc = subprocess.run(cmd, cwd=_PROJECT_ROOT, env=env).returncode
                metrics = _latest_metrics(result_dir) if rc == 0 else {}
                rows.append({
                    'model': model, 'task': task.id, 'strategy': strategy,
                    'rc': rc,
                    'correct': metrics.get('correct'),
                    'cost': metrics.get('cost'),
                })

    if dry_run or not rows:
        return
    summary = pd.DataFrame(rows)
    out_root.mkdir(parents=True, exist_ok=True)
    summary_path = out_root / 'summary.csv'
    summary.to_csv(summary_path, index=False)
    print(f'\n{"="*70}\n  Summary  (saved {summary_path})\n{"="*70}')
    print(summary.to_string(index=False))


if __name__ == '__main__':
    app()