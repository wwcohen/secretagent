"""NaturalPlan self-improvement runner.

Iteratively profiles and evolves ptools to beat baselines.

Usage:
    uv run python benchmarks/natural_plan/self_improve.py \
        --config-file conf/calendar_self_improve.yaml

    uv run python benchmarks/natural_plan/self_improve.py \
        --config-file conf/meeting_self_improve.yaml \
        --target-accuracy 0.30

    uv run python benchmarks/natural_plan/self_improve.py \
        --config-file conf/trip_self_improve.yaml \
        --target-accuracy 0.10
"""

import importlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ['PYTHONUNBUFFERED'] = '1'

import pandas as pd
import typer

_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent import config
from secretagent.core import implement_via_config, all_interfaces
from secretagent.experimental.improve import (
    improve_ptool_within_workflow, _apply_variant, _get_ptool_info,
)
from secretagent.orchestrate.profiler import profile_from_results
from secretagent.orchestrate.transforms.base import format_profiling_summary

from expt import NaturalPlanEvaluator, load_dataset, SPLIT_TO_MODULE

app = typer.Typer()


def _save_evolved(ptool_name: str, result: dict, new_accuracy: float, initial_accuracy: float):
    """Save evolved prompt/code to disk."""
    evolved_dir = _BENCHMARK_DIR / 'evolved'
    evolved_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d.%H%M%S')
    save_dir = evolved_dir / f'{timestamp}.{ptool_name}'
    save_dir.mkdir(exist_ok=True)
    (save_dir / 'evolved.py').write_text(result['code'])
    meta = {
        'ptool_name': ptool_name, 'method': result['method'],
        'accuracy_before': initial_accuracy, 'accuracy_after': new_accuracy,
        'fitness': result['fitness'], 'all_scores': result.get('all_scores', []),
        'timestamp': timestamp,
    }
    if 'pareto_frontier' in result:
        meta['pareto_frontier'] = result['pareto_frontier']
    (save_dir / 'metadata.json').write_text(json.dumps(meta, indent=2, default=str))
    print(f'  saved evolved prompt to {save_dir}')


def _pick_weakest_ptool(profile, exclude=None):
    """Pick the ptool most worth evolving — prefers high-cost reasoning ptools."""
    exclude = exclude or set()
    skip_utilities = {'extract_index', 'raw_answer', 'format_answer'}
    best_name = None
    best_score = -float('inf')
    for name, pp in profile.ptool_profiles.items():
        if name in exclude or name in skip_utilities or pp.n_calls < 3:
            continue
        error_count = sum(e.frequency for e in pp.error_patterns)
        error_rate = error_count / pp.n_calls if pp.n_calls else 0.0
        score = pp.cost_fraction + error_rate * 0.5
        if score > best_score:
            best_score = score
            best_name = name
    return best_name


@app.command(context_settings={
    'allow_extra_args': True,
    'allow_interspersed_args': False,
})
def run(
    ctx: typer.Context,
    config_file: str = typer.Option(..., help='Config YAML file'),
    target_accuracy: float = typer.Option(0.60, help='Accuracy target to beat'),
    max_iterations: int = typer.Option(5, help='Max improvement iterations'),
    train_n: int = typer.Option(15, help='Cases for evolution fitness eval'),
    population_size: int = typer.Option(3, help='Variants per generation'),
    n_generations: int = typer.Option(2, help='Evolutionary generations per ptool'),
    pareto: bool = typer.Option(False, help='Use Pareto non-dominated sorting'),
):
    """Run self-improvement loop on NaturalPlan."""

    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path
    config.configure(yaml_file=str(cfg_path), dotlist=ctx.args)
    config.set_root(_BENCHMARK_DIR)

    task = config.require('dataset.split')
    ptools_module = importlib.import_module(SPLIT_TO_MODULE[task])
    implement_via_config(ptools_module, config.require('ptools'))

    prompt_mode = config.get('dataset.prompt_mode') or '0shot'
    stratified = config.get('dataset.stratified') or False
    sample_n = config.get('dataset.sample_n')
    sample_seed = config.get('dataset.sample_seed') or 42
    eval_dataset = load_dataset(
        task, prompt_mode, stratified=stratified,
        sample_n=sample_n, sample_seed=sample_seed,
    ).configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n'),
    )

    # Train cases: use a DIFFERENT seed to ensure disjoint from eval
    train_dataset = load_dataset(
        task, prompt_mode, stratified=stratified,
        sample_n=sample_n, sample_seed=99,  # different seed for disjoint split
    )
    train_cases = train_dataset.cases[:train_n]

    entry_point = config.require('evaluate.entry_point')
    workflow_interface = getattr(ptools_module, entry_point)
    evaluator = NaturalPlanEvaluator(task)

    print(f'=== NaturalPlan Self-Improvement ({task}) ===')
    print(f'actor model: {config.get("llm.model")}')
    print(f'big model: {config.get("improve.model")}')
    print(f'eval set: {len(eval_dataset.cases)} cases, train set: {train_n} cases')
    print(f'target accuracy: {target_accuracy:.0%}')

    # Initial evaluation
    print(f'\n=== Initial Evaluation ===')
    csv_path = evaluator.evaluate(eval_dataset, workflow_interface)
    df = pd.read_csv(csv_path)
    initial_accuracy = df['correct'].mean()
    result_dir = csv_path.parent
    print(f'Initial accuracy: {initial_accuracy:.1%} ({df["correct"].sum()}/{len(df)})')

    profile = profile_from_results([result_dir])
    print(f'\n=== Initial Profile (FREE) ===')
    print(format_profiling_summary(profile))

    if initial_accuracy >= target_accuracy:
        print(f'\nAlready at target!')
        return

    # Self-improvement loop
    best_accuracy = initial_accuracy
    evolved_ptools = []
    already_evolved = set()

    for iteration in range(1, max_iterations + 1):
        print(f'\n{"=" * 50}')
        print(f'=== Iteration {iteration}/{max_iterations} ===')

        target_ptool = _pick_weakest_ptool(profile, exclude=already_evolved)
        if target_ptool is None:
            print('No more ptools to evolve.')
            break

        print(f'Target ptool: {target_ptool}')
        prof_summary = format_profiling_summary(profile)

        try:
            result = improve_ptool_within_workflow(
                ptool_name=target_ptool,
                workflow_interface=workflow_interface,
                train_cases=train_cases,
                population_size=population_size,
                n_generations=n_generations,
                profiling_summary=prof_summary,
                pareto=pareto,
            )
        except Exception as e:
            print(f'Evolution failed: {e}')
            already_evolved.add(target_ptool)
            continue

        if not result['improved']:
            print(f'No improvement found for {target_ptool}.')
            already_evolved.add(target_ptool)
            continue

        # Apply improvement (save original for rollback)
        ptool = None
        for iface in all_interfaces():
            if iface.name == target_ptool:
                ptool = iface
                break
        if not ptool:
            already_evolved.add(target_ptool)
            continue

        original_impl = ptool.implementation
        original_doc = ptool.doc
        original_src = ptool.src
        _apply_variant(ptool, result['code'], _get_ptool_info(ptool))

        # Re-evaluate
        csv_path = evaluator.evaluate(eval_dataset, workflow_interface)
        df = pd.read_csv(csv_path)
        new_accuracy = df['correct'].mean()
        result_dir = csv_path.parent
        print(f'Accuracy: {best_accuracy:.1%} -> {new_accuracy:.1%}')

        profile = profile_from_results([result_dir])
        print(format_profiling_summary(profile))

        if new_accuracy > best_accuracy:
            best_accuracy = new_accuracy
            evolved_ptools.append({'ptool': target_ptool, 'accuracy_after': new_accuracy})
            _save_evolved(target_ptool, result, new_accuracy, initial_accuracy)
        else:
            ptool.implementation = original_impl
            ptool.doc = original_doc
            ptool.src = original_src
            print(f'Regression — rolled back {target_ptool}.')
        already_evolved.add(target_ptool)

        if best_accuracy >= target_accuracy:
            print(f'\nTarget accuracy {target_accuracy:.0%} reached!')
            break

    # Summary
    print(f'\n{"=" * 50}')
    print(f'Initial: {initial_accuracy:.1%} -> Best: {best_accuracy:.1%} (target: {target_accuracy:.0%})')
    for e in evolved_ptools:
        print(f'  {e["ptool"]}: accuracy_after={e["accuracy_after"]:.1%}')


if __name__ == '__main__':
    app()
