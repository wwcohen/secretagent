"""Population-based pipeline optimizer for MedCalc.

Runs the population optimizer to find the best config for the L4 pipeline.
Uses profiling data to guide transforms (upgrade, swap_strategy, etc.).

Usage:
    uv run python benchmarks/medcalc/run_population.py \
        --config-file conf/population.yaml \
        --eval-n 2 \
        --final-n 4

    eval-n: questions per calculator for optimization eval rounds (default: 2)
    final-n: questions per calculator for final reporting (default: 4)
"""

import os
import sys
from pathlib import Path

os.environ['PYTHONUNBUFFERED'] = '1'

import pandas as pd
import typer

_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config
from secretagent.orchestrate.improve import improve_pipeline, get_transform
from secretagent.orchestrate.profiler import profile_from_results
from secretagent.orchestrate.transforms.base import format_profiling_summary

from expt import MedCalcEvaluator, setup, load_dataset, stratified_sample

app = typer.Typer()


def _eval_round(eval_cases, workflow_interface, tag='eval'):
    """Run a single evaluation round, return (accuracy, cost, result_dir)."""
    from secretagent.dataset import Dataset
    eval_dataset = Dataset(
        name='medcalc', split='train',
        cases=list(eval_cases),
    )
    evaluator = MedCalcEvaluator()
    csv_path = evaluator.evaluate(eval_dataset, workflow_interface)
    df = pd.read_csv(csv_path)
    accuracy = df['correct'].mean()
    total_cost = df['cost'].sum() if 'cost' in df.columns else 0.0
    result_dir = csv_path.parent
    n_correct = int(df['correct'].sum())
    print(f'  [{tag}] accuracy={accuracy:.1%} ({n_correct}/{len(df)}), cost=${total_cost:.4f}')
    return accuracy, total_cost, result_dir


@app.command(context_settings={
    'allow_extra_args': True,
    'allow_interspersed_args': False,
})
def run(
    ctx: typer.Context,
    config_file: str = typer.Option(..., help='Config YAML file'),
    eval_n: int = typer.Option(2, help='Questions per calculator for eval rounds'),
    final_n: int = typer.Option(4, help='Questions per calculator for final report'),
    target_accuracy: float = typer.Option(1.0, help='Target accuracy (1.0 = perpetual)'),
    max_iterations: int = typer.Option(None, help='Override improve.max_iterations'),
):
    """Run population-based optimization on MedCalc pipeline."""

    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path

    # Setup config + dataset + interfaces
    eval_dataset, workflow_interface = setup(ctx, cfg_path)

    if max_iterations is not None:
        config.configure(cfg={'improve': {'max_iterations': max_iterations}})

    # Get full train set for drawing samples
    full_train = load_dataset('train')
    all_cases = full_train.cases
    num_calcs = len(set(
        (c.metadata or {}).get('calculator_name', '') for c in all_cases
    ))
    print(f'Full train set: {len(all_cases)} cases, {num_calcs} calculators')

    # Create eval sample (eval_n per calculator)
    eval_target = num_calcs * eval_n
    eval_cases = stratified_sample(all_cases, eval_target, seed=42)
    print(f'Eval sample: {len(eval_cases)} cases ({eval_n}/calc)')

    # Create final reporting sample (final_n per calculator, different seed)
    final_target = num_calcs * final_n
    final_cases = stratified_sample(all_cases, final_target, seed=99)
    print(f'Final sample: {len(final_cases)} cases ({final_n}/calc)')

    # === BASELINE ===
    print(f'\n{"=" * 60}')
    print(f'=== BASELINE EVALUATION (eval set, {len(eval_cases)} cases) ===')
    baseline_acc, baseline_cost, baseline_dir = _eval_round(
        eval_cases, workflow_interface, tag='baseline',
    )

    # Profile baseline
    profile = profile_from_results([baseline_dir])
    print(f'\n=== Baseline Profile ===')
    print(format_profiling_summary(profile))

    # === POPULATION OPTIMIZATION ===
    print(f'\n{"=" * 60}')
    print(f'=== POPULATION OPTIMIZATION ===')
    print(f'population_size={config.get("improve.population_size", 3)}')
    print(f'max_iterations={config.get("improve.max_iterations", 5)}')
    print(f'meta_model={config.get("improve.meta_model", "heuristic")}')
    print(f'budget=${config.get("improve.budget", "unlimited")}')

    # Build a minimal Pipeline wrapper for the workflow
    # The L4 pipeline uses direct Python, so we wrap it for profiling
    from secretagent.orchestrate.pipeline import Pipeline, _entry_signature_from_interface
    from secretagent.orchestrate.catalog import PtoolCatalog
    from secretagent.core import all_interfaces

    entry_sig = _entry_signature_from_interface(workflow_interface)
    # Build catalog of available ptools (excluding entry point)
    exclude = {workflow_interface.name}
    tool_interfaces = [
        iface for iface in all_interfaces()
        if iface.name not in exclude and iface.implementation is not None
    ]
    catalog = PtoolCatalog.from_interfaces(tool_interfaces)

    # Create a delegate Pipeline that calls the workflow interface.
    # For config-only transforms (swap_strategy, upgrade, downgrade),
    # Pipeline code doesn't matter — only the profiling data drives decisions.
    ns = {workflow_interface.name: workflow_interface}
    ns.update({iface.name: iface for iface in tool_interfaces})
    delegate_body = (
        f'    return {workflow_interface.name}'
        f'({", ".join(p for p in workflow_interface.annotations if p != "return")})'
    )
    pipeline = Pipeline(delegate_body, entry_sig, ns)

    # Build run_eval_fn callback
    def run_eval_fn():
        """Re-evaluate current config on eval sample."""
        _, _, result_dir = _eval_round(eval_cases, workflow_interface, tag='re-eval')
        return [result_dir]

    # Get transforms (config-only transforms are most useful here)
    transform_names = config.get('orchestrate.improve.transforms', None)
    if transform_names:
        transforms = [get_transform(n) for n in transform_names]
    else:
        # Use only the transforms that make sense for a direct pipeline
        config_transforms = ['swap_strategy', 'upgrade', 'downgrade', 'repair']
        transforms = []
        for name in config_transforms:
            try:
                transforms.append(get_transform(name))
            except KeyError:
                pass

    report = improve_pipeline(
        pipeline=pipeline,
        result_dirs=[baseline_dir],
        catalog=catalog,
        transforms=transforms,
        run_eval_fn=run_eval_fn,
        target_accuracy=target_accuracy,
        population_size=config.get('improve.population_size', 3),
        seed_strategy=config.get('improve.seed_strategy', 'compose_then_mutate'),
        meta_model=config.get('improve.meta_model'),
        budget=config.get('improve.budget'),
        budget_mode=config.get('improve.budget_mode', 'soft_stop'),
        minibatch_size=config.get('improve.minibatch_size', 30),
    )

    # === RESULTS ===
    print(f'\n{"=" * 60}')
    print(f'=== OPTIMIZATION RESULTS ===')
    print(f'Improved: {report.improved}')
    print(f'Best accuracy: {report.best_accuracy:.1%} (baseline: {baseline_acc:.1%})')
    if report.after_profile:
        print(format_profiling_summary(report.after_profile))

    # === FINAL EVALUATION ===
    print(f'\n{"=" * 60}')
    print(f'=== FINAL EVALUATION ({len(final_cases)} cases, {final_n}/calc) ===')
    final_acc, final_cost, final_dir = _eval_round(
        final_cases, workflow_interface, tag='FINAL',
    )

    # Detailed breakdown
    from secretagent.dataset import Dataset
    final_dataset = Dataset(name='medcalc', split='train', cases=list(final_cases))
    evaluator = MedCalcEvaluator()
    final_csv = Path(final_dir) / 'results.csv'
    if final_csv.exists():
        df = pd.read_csv(final_csv)
        # By category
        print('\nBy category:')
        for cat in sorted(df['category'].unique()):
            cat_df = df[df['category'] == cat]
            print(f'  {cat}: {cat_df["correct"].mean():.1%} ({int(cat_df["correct"].sum())}/{len(cat_df)})')
        # By calculator (top 10 worst)
        calc_acc = df.groupby('calculator_name')['correct'].mean().sort_values()
        print(f'\nWorst calculators:')
        for calc, acc in calc_acc.head(10).items():
            n = len(df[df['calculator_name'] == calc])
            print(f'  {calc}: {acc:.0%} ({n} cases)')

    print(f'\n{"=" * 60}')
    print(f'BASELINE: {baseline_acc:.1%} -> OPTIMIZED: {report.best_accuracy:.1%} -> FINAL: {final_acc:.1%}')
    print(f'Total optimization cost: ~${final_cost:.2f} (final eval)')


if __name__ == '__main__':
    app()
