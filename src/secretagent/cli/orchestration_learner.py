"""Orchestration Learner CLI: thin wrapper around `learn.OrchestrationLearner`.

A supervisor LLM iteratively improves a pipeline by analyzing failures,
proposing code changes, and evaluating them. Hill climbs on accuracy,
rolls back regressions, tracks train/eval curves.

Usage (from benchmark directory, e.g. benchmarks/medcalc/):

    uv run python -m secretagent.cli.orchestration_learner run \
        --config-file conf/workflow.yaml \
        --n-train 110 --n-eval 110 \
        --max-iterations 10

    # With custom instructions and model switching:
    uv run python -m secretagent.cli.orchestration_learner run \
        --config-file conf/workflow.yaml \
        --custom-instructions "Focus on scoring system calculators" \
        --model-change models.json \
        --supervisor-model gemini/gemini-3.1-pro-preview

    # Generate HTML report for an existing run:
    uv run python -m secretagent.cli.orchestration_learner view results/TIMESTAMP.orch_learner
"""

import os
import sys
from pathlib import Path

os.environ['PYTHONUNBUFFERED'] = '1'

import typer

_EXTRA_ARGS = {"allow_extra_args": True, "allow_interspersed_args": False}
app = typer.Typer(pretty_exceptions_enable=False)


@app.command('run', context_settings=_EXTRA_ARGS)
def run(
    ctx: typer.Context,
    config_file: str = typer.Option('', help='Starting config YAML'),
    benchmark: str = typer.Option(
        '', help='Benchmark name from orchestrate/benchmarks.yaml',
    ),
    n_train: int = typer.Option(110, help='Training set size'),
    n_eval: int = typer.Option(110, help='Eval set size'),
    max_iterations: int = typer.Option(10, help='Max improvement iterations'),
    target_accuracy: float = typer.Option(None, help='Stop when reached'),
    supervisor_model: str = typer.Option(
        'gemini/gemini-3.1-pro-preview', help='Supervisor LLM model',
    ),
    custom_instructions: str = typer.Option(
        '', help='Extra instructions (text or @filepath)',
    ),
    model_change: str = typer.Option(
        '', help='JSON file with model choices for supervisor',
    ),
    train_split: str = typer.Option('', help='Dataset split for training'),
    eval_split: str = typer.Option('', help='Dataset split for evaluation'),
    ptools_module: str = typer.Option(
        '', help='Ptools module name, e.g. ptools_murder or ptools_meeting',
    ),
    seed_orchestrate: bool = typer.Option(
        False,
        help='Generate an initial workflow from ptools before supervisor iteration',
    ),
    scratch_evolved: bool = typer.Option(
        False,
        help='Evolve a timestamped scratch ptools copy instead of benchmark-local ptools_evolved.py',
    ),
    orchestrate_task_description: str = typer.Option(
        '',
        help='Task description text, or @file, for --seed-orchestrate',
    ),
    debug: bool = typer.Option(False, help='Full transparency: echo supervisor I/O'),
    resume: str = typer.Option('', help='Resume from a previous .orch_learner run directory'),
):
    """Run supervisor-driven pipeline improvement on a benchmark.

    Iteratively improves a pipeline by calling a supervisor LLM that sees
    profiling data and failure traces. Hill climbs on accuracy, rolls back
    regressions. Reports best config on a held-out eval set.

    Run from a benchmark directory (e.g. benchmarks/medcalc/).
    Extra args are dotlist config overrides.
    """
    from secretagent.learn.orchestrate_learner import OrchestrationLearner

    benchmark_dir = Path.cwd()

    # Resolve the entry-point name early so we can pass it into the Learner
    # as `interface_name`. The Learner will also load the config, but we need
    # interface_name at construction time (it's how savefile keys work).
    # Strategy: let the Learner handle config loading; pass a placeholder
    # interface_name that fit() will later override via _entry_point_name.
    # save_implementation() resolves entry_point from _entry_point_name set
    # during fit(), falling back to evaluate.entry_point from config.
    #
    # For interface_name, we use the entry point if it's knowable from
    # the config_file or benchmark adapter; otherwise fall back to a
    # neutral placeholder. The yaml key uses interface_name.
    interface_name = _peek_entry_point(
        benchmark_dir, benchmark, config_file, ctx.args,
    )

    # Results root: where the .orch_learner directory will live.
    # Benchmark runs may be launched from the repo root; put their outputs
    # under the benchmark directory rather than the caller's cwd.
    results_base = _results_base_for_run(benchmark_dir, benchmark)

    resume_path = Path(resume) if resume else None

    learner = OrchestrationLearner(
        interface_name=interface_name,
        train_dir=str(results_base),
        benchmark_name=benchmark,
        config_file=config_file,
        n_train=n_train,
        n_eval=n_eval,
        max_iterations=max_iterations,
        target_accuracy=target_accuracy,
        supervisor_model=supervisor_model,
        custom_instructions=custom_instructions,
        model_change=model_change,
        train_split=train_split,
        eval_split=eval_split,
        ptools_module=ptools_module,
        seed_orchestrate=seed_orchestrate,
        scratch_evolved=scratch_evolved,
        orchestrate_task_description=orchestrate_task_description,
        debug=debug,
        resume=resume_path,
        dotlist_overrides=list(ctx.args),
    )

    learner.learn()

    # --- Final summary table (preserves prior CLI UX) ---
    report = learner.report_obj
    if report is None:
        return
    print(f'\n{"=" * 60}')
    print('=== Orchestration Learner Complete ===')
    print(f'{"=" * 60}')
    print(f'Best train accuracy: {report.best_train_accuracy:.1%} '
          f'(iteration {report.best_iteration})')
    if report.final_eval_accuracy is not None:
        print(f'Final eval accuracy: {report.final_eval_accuracy:.1%}')
    print(f'Total supervisor cost: ${report.total_supervisor_cost:.4f}')
    print(f'Output saved to: {learner.out_dir}')

    has_eval = any(r.eval_accuracy is not None for r in report.iterations)
    eval_hdr = f'  {"Eval":>8}' if has_eval else ''
    print('\nIteration log:')
    print(f'  {"Iter":>4}  {"Train":>8}  {"Fail":>4}  {"TO":>3}'
          f'{eval_hdr}  {"Sup $":>7}  {"Status":>10}')
    for r in report.iterations:
        status = 'KEPT' if r.kept else ('BASELINE' if r.iteration == 0 else 'ROLLBACK')
        eval_col = (f'  {r.eval_accuracy:>7.1%}'
                    if has_eval and r.eval_accuracy is not None
                    else (f'  {"—":>8}' if has_eval else ''))
        to_str = f'{r.train_timeouts:>3}' if r.train_timeouts else '  0'
        print(f'  {r.iteration:>4}  {r.train_accuracy:>7.1%}  '
              f'{r.train_failures:>4}  {to_str}{eval_col}  '
              f'${r.supervisor_cost:>6.4f}  {status:>10}')


def _peek_entry_point(
    benchmark_dir: Path,
    benchmark: str,
    config_file: str,
    extra_args: list[str],
) -> str:
    """Best-effort resolution of the entry-point name at CLI-arg parse time.

    Used as `interface_name` for the Learner (which becomes the top-level
    key in implementation.yaml). Falls back to 'entry_point' if nothing is
    resolvable — fit() sets self._entry_point_name from the actual config
    once loaded, and save_implementation() prefers that.
    """
    from secretagent import config as _cfg

    # Check dotlist overrides first (CLI wins).
    for arg in extra_args:
        if arg.startswith('evaluate.entry_point='):
            return arg.split('=', 1)[1]

    if benchmark:
        try:
            from secretagent.orchestrate.benchmark_adapter import BenchmarkAdapter
            adapter = BenchmarkAdapter(benchmark)
            return adapter.entry_point_name
        except Exception:
            pass

    if config_file:
        cfg_path = Path(config_file)
        if not cfg_path.is_absolute():
            cfg_path = benchmark_dir / cfg_path
        if cfg_path.exists():
            try:
                loaded = _cfg.load_yaml_cfg(cfg_path)
                ep = loaded.get('evaluate', {}).get('entry_point')
                if ep:
                    return str(ep)
            except Exception:
                pass

    return 'entry_point'


def _results_base_for_run(benchmark_dir: Path, benchmark: str) -> Path:
    if benchmark:
        try:
            from secretagent.orchestrate.benchmark_adapter import BenchmarkAdapter
            adapter = BenchmarkAdapter(benchmark)
            return adapter.benchmark_dir / 'results' / 'orchestration_learner'
        except Exception:
            pass
    return benchmark_dir / 'results' / 'orchestration_learner'


@app.command('view')
def view(
    run_dir: str = typer.Argument(..., help='Path to an orch_learner output directory'),
):
    """Generate HTML report for an existing run directory."""
    from secretagent.orchestrate.improve import SupervisorReport
    from secretagent.learn.orchestrate_learner import generate_html_report

    output_dir = Path(run_dir)
    report_json = output_dir / 'report.json'
    if not report_json.exists():
        print(f'Error: {report_json} not found')
        raise typer.Exit(1)

    report = SupervisorReport.model_validate_json(report_json.read_text())
    generate_html_report(report, output_dir)
    print(f'Open: {output_dir / "report.html"}')


if __name__ == '__main__':
    app()
