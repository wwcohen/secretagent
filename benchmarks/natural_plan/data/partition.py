"""Partition NaturalPlan data into train/valid/test splits (100 each).

All three splits use the SAME stratified_sample method on
(num_people, num_days) (or num_cities for trip), differing only by
seed (train=42, valid=43, test=44). All disjoint. This way per-stratum
distributions are comparable across splits, so train→test accuracy
shifts reflect real generalization, not sampling artifacts.

The earlier "shuffle the full pool then take first 100" train (the
exact set evaluated for the paper) is preserved as `{task}_train_paper.json`
for reference.

The previous 50-example splits are preserved as `{task}_{split}_50.json`
so past experiments keyed on those files (via dataset.partition=train_50
etc.) still work.

Usage:
    cd benchmarks/natural_plan
    uv run python data/partition.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable

import pandas as pd

_DATA_DIR = Path(__file__).resolve().parent
_BENCHMARK_DIR = _DATA_DIR.parent
_SECRETAGENT_ROOT = _BENCHMARK_DIR.parent.parent

sys.path.insert(0, str(_SECRETAGENT_ROOT / 'src'))
sys.path.insert(0, str(_BENCHMARK_DIR))

from secretagent.dataset import Dataset, Case


# ── Task configs ──

TASKS = {
    'calendar': {
        'data_file': 'calendar_scheduling.json',
        'strata_key': lambda inst: f"({inst['num_people']},{inst['num_days']})",
        'prompt_field': 'prompt_0shot',
        # Optional reference: paper's N=100 seed=42 shuffle eval set.
        # Saved as `{task}_train_paper.json` for backwards reference.
        'paper_eval_csv': _BENCHMARK_DIR / 'results/20260420.201651.workflow/results.csv',
    },
    'meeting': {
        'data_file': 'meeting_planning.json',
        'strata_key': lambda inst: str(inst['num_people']),
        'prompt_field': 'prompt_0shot',
        'paper_eval_csv': _BENCHMARK_DIR / 'results/20260421.021958.structured_baseline/results.csv',
    },
    'trip': {
        'data_file': 'trip_planning.json',
        'strata_key': lambda inst: str(inst['num_cities']),
        'prompt_field': 'prompt_0shot',
        'paper_eval_csv': _BENCHMARK_DIR / 'results/20260421.052749.workflow/results.csv',
    },
}

# All splits stratified, disjoint. Same method, different seed.
SPLITS = {
    'train': {'seed': 42, 'n': 100},
    'valid': {'seed': 43, 'n': 100},
    'test':  {'seed': 44, 'n': 100},
}


def stratified_sample(
    data: dict[str, dict],
    strata_key: Callable[[dict], str],
    n: int,
    seed: int,
) -> dict[str, dict]:
    """Pick exactly `n` examples, distributed across strata as evenly as
    possible (round-robin across shuffled strata). Falls back to random
    if n > len(data)."""
    import random
    strata: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for k, inst in data.items():
        strata[strata_key(inst)].append((k, inst))

    rng = random.Random(seed)
    for items in strata.values():
        rng.shuffle(items)

    stratum_keys = sorted(strata.keys())
    picks: list[tuple[str, dict]] = []
    while len(picks) < n and any(strata[k] for k in stratum_keys):
        for sk in stratum_keys:
            if strata[sk] and len(picks) < n:
                picks.append(strata[sk].pop(0))
    return dict(picks[:n])


def make_cases(data: dict[str, dict], prompt_field: str) -> list[Case]:
    cases = []
    for key, inst in data.items():
        prompt = inst.get(prompt_field, inst.get('prompt_5shot', ''))
        cases.append(Case(
            name=key,
            input_args=(prompt,),
            expected_output=inst,
        ))
    return cases


def make_cases_in_order(data: dict[str, dict], ordered_keys: list[str], prompt_field: str) -> list[Case]:
    cases = []
    for key in ordered_keys:
        if key not in data:
            raise KeyError(f'case {key} not found in data')
        inst = data[key]
        prompt = inst.get(prompt_field, inst.get('prompt_5shot', ''))
        cases.append(Case(
            name=key,
            input_args=(prompt,),
            expected_output=inst,
        ))
    return cases


def save_dataset(filepath: Path, task: str, split: str, cases: list[Case]):
    dataset = Dataset(
        name=f'naturalplan_{task}',
        split=f'{task}_{split}',
        cases=cases,
    )
    with open(filepath, 'w') as fp:
        fp.write(dataset.model_dump_json(indent=2))
    print(f'  {filepath.name}: {len(cases)} cases')


def partition_task(task: str, cfg: dict):
    data_path = _DATA_DIR / cfg['data_file']
    with open(data_path) as f:
        all_data = json.load(f)

    print(f'{task}: {len(all_data)} total examples')

    # --- All three splits: stratified, disjoint, different seeds ---
    used_keys: set[str] = set()
    for split_name, split_cfg in SPLITS.items():
        available = {k: v for k, v in all_data.items() if k not in used_keys}
        sampled = stratified_sample(
            available, cfg['strata_key'], split_cfg['n'], split_cfg['seed'],
        )
        used_keys.update(sampled.keys())
        cases = make_cases(sampled, cfg['prompt_field'])
        save_dataset(_DATA_DIR / f'{task}_{split_name}.json', task, split_name, cases)

    # --- For reference: paper's seed=42 shuffle eval set as *_train_paper.json ---
    paper_csv = cfg.get('paper_eval_csv')
    if paper_csv and paper_csv.exists():
        paper_names = pd.read_csv(paper_csv)['case_name'].tolist()
        missing = [n for n in paper_names if n not in all_data]
        if not missing:
            paper_cases = make_cases_in_order(all_data, paper_names, cfg['prompt_field'])
            save_dataset(_DATA_DIR / f'{task}_train_paper.json', task, 'train_paper', paper_cases)


if __name__ == '__main__':
    for task, cfg in TASKS.items():
        partition_task(task, cfg)
    print('\nDone. train/valid/test splits created (100 each, all stratified, disjoint).')
    print('  train = stratified seed=42, valid = stratified seed=43, test = stratified seed=44')
    print('  *_train_paper.json = the paper\'s original seed=42-shuffle eval set (reference)')
    print('  *_50.json = the older 50-example splits (legacy)')
