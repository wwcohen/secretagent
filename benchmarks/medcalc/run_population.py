"""Population-based pipeline optimizer for MedCalc.

Runs the population optimizer (meta-optimizer guided) to find the best config
for the L4 pipeline. All LLM calls now go through interfaces, so the profiler
can see every ptool's cost, error rate, and performance.

Usage:
    uv run python benchmarks/medcalc/run_population.py \
        --config-file conf/population.yaml \
        --eval-n 2 \
        --final-n 4
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
from secretagent.core import implement_via_config
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
    exact_match = df['exact_match'].mean() if 'exact_match' in df.columns else accuracy
    total_cost = df['cost'].sum() if 'cost' in df.columns else 0.0
    n_correct = int(df['correct'].sum())
    print(f'  [{tag}] accuracy={accuracy:.1%} ({n_correct}/{len(df)}), '
          f'exact={exact_match:.1%}, cost=${total_cost:.4f}')
    return accuracy, total_cost, csv_path.parent


@app.command(context_settings={
    'allow_extra_args': True,
    'allow_interspersed_args': False,
})
def run(
    ctx: typer.Context,
    config_file: str = typer.Option(..., help='Config YAML file'),
    eval_n: int = typer.Option(2, help='Questions per calc for eval'),
    final_n: int = typer.Option(4, help='Questions per calc for final report'),
    max_iterations: int = typer.Option(None, help='Override max iterations'),
):
    """Run population-based optimization on MedCalc pipeline."""

    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path

    # Setup config + dataset + interfaces
    eval_dataset, workflow_interface = setup(ctx, cfg_path)

    # Load full train set for sample creation
    full_train = load_dataset('train')
    all_cases = full_train.cases
    num_calcs = len(set(
        (c.metadata or {}).get('calculator_name', '') for c in all_cases
    ))
    print(f'Full train set: {len(all_cases)} cases, {num_calcs} calculators')

    eval_cases = stratified_sample(all_cases, num_calcs * eval_n, seed=42)
    print(f'Eval sample: {len(eval_cases)} cases ({eval_n}/calc)')

    final_cases = stratified_sample(all_cases, num_calcs * final_n, seed=99)
    print(f'Final sample: {len(final_cases)} cases ({final_n}/calc)')

    # === BASELINE ===
    print(f'\n{"=" * 60}')
    print(f'=== BASELINE ({config.get("llm.model")}) ===')
    baseline_acc, baseline_cost, baseline_dir = _eval_round(
        eval_cases, workflow_interface, tag='baseline',
    )

    # Profile baseline — should now show ALL ptools
    profile = profile_from_results([baseline_dir])
    print(f'\n=== Baseline Profile ===')
    print(format_profiling_summary(profile))

    # === POPULATION OPTIMIZATION ===
    print(f'\n{"=" * 60}')
    print(f'=== POPULATION OPTIMIZATION (meta-optimizer guided) ===')

    from secretagent.orchestrate.pipeline import Pipeline, _entry_signature_from_interface
    from secretagent.orchestrate.catalog import PtoolCatalog
    from secretagent.core import all_interfaces

    entry_sig = _entry_signature_from_interface(workflow_interface)
    exclude = {workflow_interface.name}
    tool_interfaces = [
        iface for iface in all_interfaces()
        if iface.name not in exclude and iface.implementation is not None
    ]
    catalog = PtoolCatalog.from_interfaces(tool_interfaces)

    # Create delegate pipeline
    ns = {workflow_interface.name: workflow_interface}
    ns.update({iface.name: iface for iface in tool_interfaces})
    params = [p for p in workflow_interface.annotations if p != 'return']
    delegate_body = f'    return {workflow_interface.name}({", ".join(params)})'
    pipeline = Pipeline(delegate_body, entry_sig, ns)

    # Build re-evaluation callback
    import ptools as ptools_mod

    def run_eval_fn():
        """Re-bind ptools from current config and re-evaluate."""
        implement_via_config(ptools_mod, config.require('ptools'))
        _, _, result_dir = _eval_round(eval_cases, workflow_interface, tag='re-eval')
        return [result_dir]

    # Use all transforms
    transform_names = config.get('orchestrate.improve.transforms', None)
    if transform_names:
        transforms = [get_transform(n) for n in transform_names]
    else:
        available = ['swap_strategy', 'upgrade', 'downgrade', 'repair']
        transforms = []
        for name in available:
            try:
                transforms.append(get_transform(name))
            except KeyError:
                pass

    iters = max_iterations if max_iterations is not None else config.get('improve.max_iterations', 5)
    report = improve_pipeline(
        pipeline=pipeline,
        result_dirs=[baseline_dir],
        catalog=catalog,
        transforms=transforms,
        max_iterations=iters,
        run_eval_fn=run_eval_fn,
        target_accuracy=1.0,
        population_size=config.get('improve.population_size', 3),
        seed_strategy=config.get('improve.seed_strategy', 'compose_then_mutate'),
        meta_model=config.get('improve.meta_model'),
        budget=config.get('improve.budget'),
        budget_mode=config.get('improve.budget_mode', 'soft_stop'),
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

    final_csv = Path(final_dir) / 'results.csv'
    if final_csv.exists():
        df = pd.read_csv(final_csv)
        print(f'\nBy category:')
        for cat in sorted(df['category'].unique()):
            cat_df = df[df['category'] == cat]
            print(f'  {cat}: {cat_df["correct"].mean():.1%} '
                  f'({int(cat_df["correct"].sum())}/{len(cat_df)})')
        calc_acc = df.groupby('calculator_name')['correct'].mean().sort_values()
        print(f'\nWorst calculators:')
        for calc, acc in calc_acc.head(10).items():
            n = len(df[df['calculator_name'] == calc])
            print(f'  {calc}: {acc:.0%} ({n} cases)')

    print(f'\n{"=" * 60}')
    print(f'BASELINE: {baseline_acc:.1%} -> OPTIMIZED: {report.best_accuracy:.1%} -> FINAL: {final_acc:.1%}')


if __name__ == '__main__':
    app()
