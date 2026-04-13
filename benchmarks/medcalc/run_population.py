"""Population-based config optimizer for MedCalc.

Evaluates different model/method configurations for the L4 pipeline ptools,
tracking results in a Population with BudgetTracker. The extraction pipeline
uses llm.model directly (via llm_util.llm), so model upgrades affect all
LLM-backed stages including inline extraction.

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
from secretagent.orchestrate.budget import BudgetTracker
from secretagent.orchestrate.population import PipelineCandidate, Population

from expt import MedCalcEvaluator, load_dataset, stratified_sample

app = typer.Typer()

# Models to explore, ordered by estimated strength
_MODELS = [
    'together_ai/deepseek-ai/DeepSeek-V3.1',           # $0.60/$1.70 — strong reasoning
    'together_ai/Qwen/Qwen3.5-397B-A17B',              # $0.60/$3.60 — large MoE
    'together_ai/moonshotai/Kimi-K2.5',                 # $0.50/$2.80 — good all-round
    'together_ai/Qwen/Qwen3-235B-A22B-Instruct-2507-tput',  # $0.20/$0.60 — efficient
]

# Method variants to try for the identify_calculator ptool
_IDENTIFY_METHODS = ['simulate', 'prompt_llm']


def _setup_base(cfg_path, dotlist_args):
    """Load config without binding ptools (we re-bind per candidate)."""
    config.configure(yaml_file=cfg_path, dotlist=dotlist_args)
    config.set_root(_BENCHMARK_DIR)


def _bind_and_eval(eval_cases, cfg_overrides, tag='eval'):
    """Apply config overrides, re-bind ptools, evaluate, return metrics."""
    import ptools as ptools_mod

    # Apply config overrides
    if cfg_overrides:
        dotlist = [f'{k}={v}' for k, v in cfg_overrides.items()]
        config.configure(dotlist=dotlist)

    # Re-bind interfaces from config
    implement_via_config(ptools_mod, config.require('ptools'))

    entry_point_name = config.get('evaluate.entry_point', 'calculate_medical_value')
    workflow_interface = getattr(ptools_mod, entry_point_name)

    from secretagent.dataset import Dataset
    eval_dataset = Dataset(name='medcalc', split='train', cases=list(eval_cases))
    evaluator = MedCalcEvaluator()
    csv_path = evaluator.evaluate(eval_dataset, workflow_interface)
    df = pd.read_csv(csv_path)

    accuracy = df['correct'].mean()
    exact_match = df['exact_match'].mean() if 'exact_match' in df.columns else accuracy
    total_cost = df['cost'].sum() if 'cost' in df.columns else 0.0
    n_correct = int(df['correct'].sum())

    # Per-case scores for Pareto front
    instance_scores = {}
    for _, row in df.iterrows():
        case_name = row.get('case_name', str(row.name))
        instance_scores[case_name] = float(row['correct'])

    print(f'  [{tag}] accuracy={accuracy:.1%} ({n_correct}/{len(df)}), '
          f'exact={exact_match:.1%}, cost=${total_cost:.4f}')

    return {
        'accuracy': accuracy, 'exact_match': exact_match,
        'cost': total_cost, 'instance_scores': instance_scores,
        'result_dir': csv_path.parent,
    }


@app.command(context_settings={
    'allow_extra_args': True,
    'allow_interspersed_args': False,
})
def run(
    ctx: typer.Context,
    config_file: str = typer.Option(..., help='Config YAML file'),
    eval_n: int = typer.Option(2, help='Questions per calc for eval'),
    final_n: int = typer.Option(4, help='Questions per calc for final report'),
):
    """Run population-based config optimization on MedCalc pipeline."""

    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path

    _setup_base(cfg_path, ctx.args)
    budget = BudgetTracker(
        budget_limit=config.get('improve.budget', 25.0),
        mode=config.get('improve.budget_mode', 'soft_stop'),
    )

    # Load full train set
    full_train = load_dataset('train')
    all_cases = full_train.cases
    num_calcs = len(set(
        (c.metadata or {}).get('calculator_name', '') for c in all_cases
    ))
    print(f'Full train set: {len(all_cases)} cases, {num_calcs} calculators')

    # Create eval sample (eval_n per calc)
    eval_cases = stratified_sample(all_cases, num_calcs * eval_n, seed=42)
    print(f'Eval sample: {len(eval_cases)} cases ({eval_n}/calc)')

    # Create final sample (final_n per calc, different seed)
    final_cases = stratified_sample(all_cases, num_calcs * final_n, seed=99)
    print(f'Final sample: {len(final_cases)} cases ({final_n}/calc)')

    # === BASELINE ===
    print(f'\n{"=" * 60}')
    print(f'=== BASELINE ({config.get("llm.model")}) ===')
    baseline = _bind_and_eval(eval_cases, {}, tag='baseline')
    budget.record(baseline['cost'], 'baseline eval')

    # Initialize population
    from secretagent.orchestrate.pipeline import Pipeline
    dummy_pipeline = Pipeline('pass', 'def f():', {})
    population = Population(population_size=len(_MODELS) * 2)

    seed = PipelineCandidate(
        pipeline=dummy_pipeline,
        config={'llm.model': config.get('llm.model')},
        instance_scores=baseline['instance_scores'],
        generation=0,
        mutation_history=['baseline'],
    )
    population.add(seed)

    best_accuracy = baseline['accuracy']
    best_config = {}
    results_log = [{'tag': 'baseline', 'config': {}, **baseline}]

    # === EXPLORATION: Try different models ===
    print(f'\n{"=" * 60}')
    print(f'=== MODEL EXPLORATION ===')

    for model in _MODELS:
        if model == config.get('llm.model'):
            continue  # skip baseline model
        if budget.should_stop():
            print(f'  budget exhausted, stopping exploration')
            break

        tag = model.split('/')[-1]
        print(f'\n--- Trying llm.model={tag} ---')
        overrides = {'llm.model': model}
        result = _bind_and_eval(eval_cases, overrides, tag=tag)
        budget.record(result['cost'], f'model={tag}')

        cand = PipelineCandidate(
            pipeline=dummy_pipeline,
            config=overrides,
            instance_scores=result['instance_scores'],
            generation=1,
            parent_index=0,
            mutation_history=[f'model→{tag}'],
        )
        population.add(cand)
        results_log.append({'tag': tag, 'config': overrides, **result})

        if result['accuracy'] > best_accuracy:
            best_accuracy = result['accuracy']
            best_config = overrides
            print(f'  *** NEW BEST: {best_accuracy:.1%} ***')

        print(f'  {budget.format_summary()}')

    # === EXPLORATION: Try method variants for identify_calculator ===
    print(f'\n{"=" * 60}')
    print(f'=== METHOD EXPLORATION (identify_calculator) ===')

    # Use the best model found so far
    base_model = best_config.get('llm.model', config.get('llm.model'))

    for method in _IDENTIFY_METHODS:
        current_method = config.get('ptools.identify_calculator.method', 'simulate')
        if method == current_method:
            continue
        if budget.should_stop():
            break

        tag = f'{base_model.split("/")[-1]}+id_{method}'
        print(f'\n--- Trying identify_calculator.method={method} ---')
        overrides = {
            'llm.model': base_model,
            'ptools.identify_calculator.method': method,
        }
        result = _bind_and_eval(eval_cases, overrides, tag=tag)
        budget.record(result['cost'], f'method={tag}')

        cand = PipelineCandidate(
            pipeline=dummy_pipeline,
            config=overrides,
            instance_scores=result['instance_scores'],
            generation=2,
            parent_index=0,
            mutation_history=[f'model→{base_model.split("/")[-1]}', f'id→{method}'],
        )
        population.add(cand)
        results_log.append({'tag': tag, 'config': overrides, **result})

        if result['accuracy'] > best_accuracy:
            best_accuracy = result['accuracy']
            best_config = overrides
            print(f'  *** NEW BEST: {best_accuracy:.1%} ***')

    # === POPULATION SUMMARY ===
    print(f'\n{"=" * 60}')
    print(f'=== POPULATION SUMMARY ===')
    print(population.summary())
    front = population.pareto_front()
    print(f'Pareto front indices: {front}')

    # === APPLY BEST CONFIG ===
    print(f'\n{"=" * 60}')
    print(f'=== BEST CONFIG ===')
    print(f'Best accuracy: {best_accuracy:.1%}')
    for k, v in best_config.items():
        print(f'  {k}: {v}')

    # === FINAL EVALUATION ===
    print(f'\n{"=" * 60}')
    print(f'=== FINAL EVALUATION ({len(final_cases)} cases, {final_n}/calc) ===')
    final = _bind_and_eval(final_cases, best_config, tag='FINAL')
    budget.record(final['cost'], 'final eval')

    # Detailed breakdown
    final_csv = Path(final['result_dir']) / 'results.csv'
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

    # === SUMMARY ===
    print(f'\n{"=" * 60}')
    print(f'BASELINE: {baseline["accuracy"]:.1%} -> BEST EVAL: {best_accuracy:.1%} -> FINAL: {final["accuracy"]:.1%}')
    print(budget.format_summary())

    # Results table
    print(f'\nAll configurations tested:')
    print(f'{"Tag":<40} {"Accuracy":>10} {"Exact":>10} {"Cost":>10}')
    print('-' * 72)
    for r in sorted(results_log, key=lambda x: x['accuracy'], reverse=True):
        print(f'{r["tag"]:<40} {r["accuracy"]:>10.1%} {r["exact_match"]:>10.1%} ${r["cost"]:>9.4f}')


if __name__ == '__main__':
    app()
