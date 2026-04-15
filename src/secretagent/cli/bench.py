"""Universal benchmark runner.

Dispatch layer on top of per-benchmark runners. Each benchmark is run
as a subprocess with appropriate config overrides.

Usage:
    uv run -m secretagent.cli.bench list
    uv run -m secretagent.cli.bench run sports_understanding
    uv run -m secretagent.cli.bench run medcalc --minibatch
    uv run -m secretagent.cli.bench run-all --minibatch
"""

import subprocess
from pathlib import Path

import typer

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}
app = typer.Typer(pretty_exceptions_enable=False)

# Resolve benchmarks/ directory relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_BENCH_ROOT = _PROJECT_ROOT / 'benchmarks'

BENCHMARKS = {
    'sports_understanding': {
        'directory': 'bbh/sports_understanding',
        'command': 'uv run python -m secretagent.cli.expt run --interface ptools.are_sports_in_sentence_consistent',
        'eval_split': 'dataset.split=valid',
        'strat_key': None,
        'eval_pool_size': 75,
        'default_minibatch': 20,
        'default_overrides': ['ptools.are_sports_in_sentence_consistent.method=simulate'],
    },
    'geometric_shapes': {
        'directory': 'bbh/geometric_shapes',
        'command': 'uv run python -m secretagent.cli.expt run --interface ptools.identify_shape',
        'eval_split': 'dataset.split=valid',
        'strat_key': None,
        'eval_pool_size': 75,
        'default_minibatch': 20,
        'default_overrides': ['ptools.identify_shape.method=simulate'],
    },
    'penguins_in_a_table': {
        'directory': 'bbh/penguins_in_a_table',
        'command': 'uv run python -m secretagent.cli.expt run --interface ptools.answer_penguin_question',
        'eval_split': 'dataset.split=valid',
        'strat_key': None,
        'eval_pool_size': 43,
        'default_minibatch': 20,
        'default_overrides': ['ptools.answer_penguin_question.method=simulate'],
    },
    'medcalc': {
        'directory': 'medcalc',
        'command': 'uv run python expt.py run',
        'eval_split': '',
        'strat_key': 'calculator_name',
        'eval_pool_size': 220,
        'default_minibatch': 110,
        'default_overrides': [],
    },
    'musr_murder': {
        'directory': 'musr',
        'command': 'uv run python expt.py run --config-file conf/murder.yaml',
        'eval_split': 'dataset.split=murder_mysteries_val',
        'strat_key': None,
        'eval_pool_size': 75,
        'default_minibatch': 10,
        'default_overrides': [],
    },
    'musr_object': {
        'directory': 'musr',
        'command': 'uv run python expt.py run --config-file conf/object.yaml',
        'eval_split': 'dataset.split=object_placements_val',
        'strat_key': None,
        'eval_pool_size': 75,
        'default_minibatch': 10,
        'default_overrides': ['ptools.extract_movements.method=simulate'],
    },
    'musr_team': {
        'directory': 'musr',
        'command': 'uv run python expt.py run --config-file conf/team.yaml',
        'eval_split': 'dataset.split=team_allocation_val',
        'strat_key': None,
        'eval_pool_size': 75,
        'default_minibatch': 10,
        'default_overrides': [],
    },
    'natural_plan_calendar': {
        'directory': 'natural_plan',
        'command': 'uv run python expt.py run --config-file conf/calendar.yaml',
        'eval_split': 'dataset.partition=valid',
        'strat_key': None,
        'eval_pool_size': 50,
        'default_minibatch': 10,
        'default_overrides': ['ptools.calendar_scheduling.method=simulate'],
    },
    'natural_plan_meeting': {
        'directory': 'natural_plan',
        'command': 'uv run python expt.py run --config-file conf/meeting.yaml',
        'eval_split': 'dataset.partition=valid',
        'strat_key': None,
        'eval_pool_size': 50,
        'default_minibatch': 10,
        'default_overrides': ['ptools.meeting_planning.method=simulate'],
    },
    'natural_plan_trip': {
        'directory': 'natural_plan',
        'command': 'uv run python expt.py run --config-file conf/trip.yaml',
        'eval_split': 'dataset.partition=valid',
        'strat_key': None,
        'eval_pool_size': 48,
        'default_minibatch': 10,
        'default_overrides': ['ptools.trip_planning.method=simulate'],
    },
    'rulearena_airline': {
        'directory': 'rulearena',
        'command': 'uv run python expt.py run',
        'eval_split': 'dataset.split=valid dataset.domain=airline',
        'strat_key': None,
        'eval_pool_size': 60,
        'default_minibatch': 10,
        'default_overrides': ['ptools.compute_rulearena_answer.method=simulate'],
    },
    'rulearena_nba': {
        'directory': 'rulearena',
        'command': 'uv run python expt.py run',
        'eval_split': 'dataset.split=valid dataset.domain=nba',
        'strat_key': None,
        'eval_pool_size': 42,
        'default_minibatch': 10,
        'default_overrides': ['ptools.compute_rulearena_answer.method=simulate'],
    },
    'rulearena_tax': {
        'directory': 'rulearena',
        'command': 'uv run python expt.py run',
        'eval_split': 'dataset.split=valid dataset.domain=tax',
        'strat_key': None,
        'eval_pool_size': 60,
        'default_minibatch': 10,
        'default_overrides': ['ptools.compute_rulearena_answer.method=simulate'],
    },
    'tabmwp': {
        'directory': 'tabmwp',
        'command': 'uv run python expt.py run',
        'eval_split': 'dataset.split=dev1k',
        'strat_key': 'ques_type',
        'eval_pool_size': 1000,
        'default_minibatch': 50,
        'default_overrides': ['ptools.tabmwp_solve.method=simulate'],
    },
}


def _build_command(bench: dict, minibatch: bool, extra_args: list[str]) -> list[str]:
    """Build the subprocess command list for a benchmark run.

    Order: command + eval_split + default_overrides + minibatch + user args.
    User args come last so they win over defaults.
    """
    parts = bench['command'].split()
    if bench['eval_split']:
        parts.extend(bench['eval_split'].split())
    parts.extend(bench.get('default_overrides', []))
    if minibatch:
        parts.append(f'dataset.n={bench["default_minibatch"]}')
    parts.extend(extra_args)
    return parts


def _run_benchmark(name: str, bench: dict, minibatch: bool, extra_args: list[str]) -> int:
    """Run a single benchmark as a subprocess. Returns exit code."""
    cmd = _build_command(bench, minibatch, extra_args)
    cwd = _BENCH_ROOT / bench['directory']
    print(f'\n{"="*60}')
    print(f'  {name}  (cwd={cwd})')
    print(f'  {" ".join(cmd)}')
    print(f'{"="*60}')
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


@app.command()
def list():
    """List all registered benchmarks."""
    print(f'{"Benchmark":<28} {"Pool":>5} {"Mini":>5}  {"Directory"}')
    print('-' * 70)
    for name, b in BENCHMARKS.items():
        print(f'{name:<28} {b["eval_pool_size"]:>5} {b["default_minibatch"]:>5}  {b["directory"]}')


@app.command(context_settings=_EXTRA_ARGS)
def run(
    ctx: typer.Context,
    benchmark: str = typer.Argument(help='Benchmark name from registry'),
    minibatch: bool = typer.Option(False, '--minibatch', help='Use default minibatch size'),
):
    """Run a single benchmark evaluation.

    Extra positional args are passed as dotlist config overrides.
    """
    if benchmark not in BENCHMARKS:
        print(f'Unknown benchmark: {benchmark}')
        print(f'Available: {", ".join(BENCHMARKS.keys())}')
        raise typer.Exit(1)
    rc = _run_benchmark(benchmark, BENCHMARKS[benchmark], minibatch, ctx.args)
    raise typer.Exit(rc)


@app.command('run-all', context_settings=_EXTRA_ARGS)
def run_all(
    ctx: typer.Context,
    minibatch: bool = typer.Option(False, '--minibatch', help='Use default minibatch size'),
):
    """Run all benchmarks sequentially.

    Extra positional args are passed as dotlist config overrides.
    """
    results = {}
    for name, bench in BENCHMARKS.items():
        rc = _run_benchmark(name, bench, minibatch, ctx.args)
        results[name] = rc

    print(f'\n{"="*60}')
    print('  Summary')
    print(f'{"="*60}')
    for name, rc in results.items():
        status = 'OK' if rc == 0 else f'FAILED (exit {rc})'
        print(f'  {name:<28} {status}')


if __name__ == '__main__':
    app()
