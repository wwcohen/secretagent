"""MUSR self-improvement runner.

Iteratively profiles and evolves ptools to beat baselines.

Usage:
    uv run python benchmarks/musr/self_improve.py \
        --config-file conf/murder_self_improve.yaml

    # override target and iterations
    uv run python benchmarks/musr/self_improve.py \
        --config-file conf/murder_self_improve.yaml \
        --target-accuracy 0.72 \
        --max-iterations 5 \
        --train-n 25

    # quick test on 4 examples
    uv run python benchmarks/musr/self_improve.py \
        --config-file conf/murder_self_improve.yaml \
        --max-iterations 1 --train-n 4 dataset.n=4
"""

import importlib
import os
import sys
from pathlib import Path

# Force unbuffered output so progress is visible in background runs
os.environ['PYTHONUNBUFFERED'] = '1'

import pandas as pd
import typer

_BENCHMARK_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

import json
from datetime import datetime

from secretagent import config
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset, Case
from secretagent.experimental.improve import (
    improve_ptool_within_workflow, _apply_variant, _get_ptool_info,
)
from secretagent.orchestrate.profiler import profile_from_results
from secretagent.orchestrate.transforms.base import format_profiling_summary

# Reuse from expt.py
from expt import MUSREvaluator, load_dataset, _resolve_module

app = typer.Typer()


def _save_evolved(ptool_name: str, result: dict, new_accuracy: float, initial_accuracy: float):
    """Save evolved prompt/code to disk for reuse and inspection."""
    evolved_dir = _BENCHMARK_DIR / 'evolved'
    evolved_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d.%H%M%S')
    save_dir = evolved_dir / f'{timestamp}.{ptool_name}'
    save_dir.mkdir(exist_ok=True)

    # Save the evolved code (docstring for simulate, function for direct)
    (save_dir / 'evolved.py').write_text(result['code'])

    # Save metadata
    meta = {
        'ptool_name': ptool_name,
        'method': result['method'],
        'accuracy_before': initial_accuracy,
        'accuracy_after': new_accuracy,
        'fitness': result['fitness'],
        'all_scores': result.get('all_scores', []),
        'generations': result.get('generations', []),
        'timestamp': timestamp,
    }
    if 'pareto_frontier' in result:
        meta['pareto_frontier'] = result['pareto_frontier']
    (save_dir / 'metadata.json').write_text(json.dumps(meta, indent=2, default=str))

    print(f'  saved evolved prompt to {save_dir}')


def _pick_weakest_ptool(profile, exclude=None):
    """Pick the ptool most worth evolving from profiling data.

    Prefers high-cost ptools (where improvement has impact) and skips
    trivial utility ptools like extract_index.
    """
    exclude = exclude or set()
    # Skip utility ptools that just parse/extract — evolving their
    # docstrings rarely helps, the real reasoning happens elsewhere
    skip_utilities = {'extract_index', 'raw_answer', 'format_answer'}
    best_name = None
    best_score = -float('inf')

    for name, pp in profile.ptool_profiles.items():
        if name in exclude or name in skip_utilities or pp.n_calls < 3:
            continue
        # Prioritize ptools that consume significant cost (reasoning ptools)
        # and have room to improve
        error_count = sum(e.frequency for e in pp.error_patterns)
        error_rate = error_count / pp.n_calls if pp.n_calls else 0.0
        # Score = cost_fraction (big is important) + error_rate (buggy)
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
    target_accuracy: float = typer.Option(0.72, help='Accuracy target to beat'),
    max_iterations: int = typer.Option(5, help='Max improvement iterations'),
    train_n: int = typer.Option(25, help='Cases for evolution fitness eval'),
    population_size: int = typer.Option(3, help='Variants per generation'),
    n_generations: int = typer.Option(2, help='Evolutionary generations per ptool'),
    pareto: bool = typer.Option(False, help='Use Pareto non-dominated sorting instead of linear fitness'),
):
    """Run self-improvement loop on MUSR."""

    # --- Setup ---
    cfg_path = Path(config_file)
    if not cfg_path.is_absolute():
        cfg_path = _BENCHMARK_DIR / cfg_path
    config.configure(yaml_file=str(cfg_path), dotlist=ctx.args)
    config.set_root(_BENCHMARK_DIR)

    split = config.require('dataset.split')
    ptools_module = importlib.import_module(_resolve_module(split))
    implement_via_config(ptools_module, config.require('ptools'))

    # Load datasets: train and eval must be DISJOINT to prevent overfitting
    eval_dataset = load_dataset(split).configure(
        shuffle_seed=config.get('dataset.shuffle_seed'),
        n=config.get('dataset.n'),
    )
    eval_names = {c.name for c in eval_dataset.cases}
    # Train: load fresh, same shuffle, take cases NOT in eval set
    train_pool = load_dataset(split).configure(shuffle_seed=42)
    train_cases = [c for c in train_pool.cases if c.name not in eval_names][:train_n]
    overlap = len(set(c.name for c in train_cases) & eval_names)
    print(f'Train: {len(train_cases)} cases, eval: {len(eval_dataset.cases)} cases, overlap: {overlap}')

    entry_point = config.require('evaluate.entry_point')
    workflow_interface = getattr(ptools_module, entry_point)
    evaluator = MUSREvaluator()

    print(f'=== MUSR Self-Improvement ===')
    print(f'split: {split}')
    print(f'actor model: {config.get("llm.model")}')
    print(f'big model: {config.get("improve.model")}')
    print(f'eval set: {len(eval_dataset.cases)} cases, train set: {train_n} cases')
    print(f'target accuracy: {target_accuracy:.0%}')
    print(f'max iterations: {max_iterations}')
    print(f'evolution: pop={population_size}, gen={n_generations}, pareto={pareto}')

    # --- Initial evaluation ---
    print(f'\n=== Initial Evaluation ===')
    csv_path = evaluator.evaluate(eval_dataset, workflow_interface)
    df = pd.read_csv(csv_path)
    initial_accuracy = df['correct'].mean()
    result_dir = csv_path.parent
    print(f'Initial accuracy: {initial_accuracy:.1%} ({df["correct"].sum()}/{len(df)})')

    # --- Profile (FREE) ---
    profile = profile_from_results([result_dir])
    print(f'\n=== Initial Profile (FREE) ===')
    print(format_profiling_summary(profile))

    if initial_accuracy >= target_accuracy:
        print(f'\nAlready at target! ({initial_accuracy:.1%} >= {target_accuracy:.0%})')
        return

    # --- Self-improvement loop ---
    best_accuracy = initial_accuracy
    evolved_ptools = []
    already_evolved = set()

    for iteration in range(1, max_iterations + 1):
        print(f'\n{"=" * 50}')
        print(f'=== Iteration {iteration}/{max_iterations} ===')
        print(f'{"=" * 50}')

        # Pick weakest ptool (skip ones we already evolved this round)
        target_ptool = _pick_weakest_ptool(profile, exclude=already_evolved)
        if target_ptool is None:
            print('No more ptools to evolve. Stopping.')
            break

        print(f'\nTarget ptool: {target_ptool}')
        pp = profile.ptool_profiles.get(target_ptool)
        if pp:
            error_count = sum(e.frequency for e in pp.error_patterns)
            print(f'  cost_fraction: {pp.cost_fraction:.1%}')
            print(f'  errors: {error_count}')
            print(f'  presence_correct: {pp.presence_in_correct:.2f}')
            print(f'  presence_incorrect: {pp.presence_in_incorrect:.2f}')
            print(f'  exception_rate: {pp.exception_rate:.2f}')

        # Evolve it
        print(f'\nEvolving {target_ptool}...')
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

        # Apply the improvement (save original for rollback)
        from secretagent.core import all_interfaces
        ptool = None
        for iface in all_interfaces():
            if iface.name == target_ptool:
                ptool = iface
                break

        if ptool is None:
            print(f'Could not find interface {target_ptool}')
            continue

        # Save original state for rollback
        original_impl = ptool.implementation
        original_doc = ptool.doc
        original_src = ptool.src

        _apply_variant(ptool, result['code'], _get_ptool_info(ptool))
        print(f'Applied improved {target_ptool}')
        print(f'  evolution fitness: accuracy={result["fitness"]["accuracy"]:.2f}, '
              f'cost={result["fitness"]["cost"]:.4f}')

        # Re-evaluate on full eval set
        print(f'\nRe-evaluating on full eval set...')
        csv_path = evaluator.evaluate(eval_dataset, workflow_interface)
        df = pd.read_csv(csv_path)
        new_accuracy = df['correct'].mean()
        result_dir = csv_path.parent
        print(f'Accuracy: {best_accuracy:.1%} -> {new_accuracy:.1%}')

        # Re-profile (FREE)
        profile = profile_from_results([result_dir])
        print(f'\n--- Profile after iteration {iteration} (FREE) ---')
        print(format_profiling_summary(profile))

        if new_accuracy > best_accuracy:
            best_accuracy = new_accuracy
            evolved_ptools.append({
                'ptool': target_ptool,
                'accuracy_after': new_accuracy,
                'code_len': len(result['code']),
            })
            # Save evolved prompt to disk
            _save_evolved(target_ptool, result, new_accuracy, initial_accuracy)
            print(f'Improvement kept! Best accuracy: {best_accuracy:.1%}')
        else:
            # Rollback to original implementation
            ptool.implementation = original_impl
            ptool.doc = original_doc
            ptool.src = original_src
            print(f'Regression — rolled back {target_ptool}.')

        already_evolved.add(target_ptool)

        if best_accuracy >= target_accuracy:
            print(f'\nTarget accuracy {target_accuracy:.0%} reached!')
            break

    # --- Summary ---
    print(f'\n{"=" * 50}')
    print(f'=== Summary ===')
    print(f'{"=" * 50}')
    print(f'Initial accuracy: {initial_accuracy:.1%}')
    print(f'Best accuracy:    {best_accuracy:.1%}')
    print(f'Target:           {target_accuracy:.0%}')
    print(f'Evolved ptools:   {len(evolved_ptools)}')
    for e in evolved_ptools:
        print(f'  {e["ptool"]}: accuracy_after={e["accuracy_after"]:.1%}')
    if best_accuracy >= target_accuracy:
        print(f'\nSUCCESS: Beat baseline!')
    else:
        print(f'\nDid not reach target. Consider more iterations or different approach.')


if __name__ == '__main__':
    app()
