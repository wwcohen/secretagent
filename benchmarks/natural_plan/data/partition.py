"""Partition NaturalPlan data into train/valid/test splits (100 each).

All three splits use the SAME stratified_sample method on
(num_people, num_days) (or num_cities for trip), differing only by
seed (train=42, valid=43, test=44). All disjoint. This way per-stratum
distributions are comparable across splits, so train->test accuracy
shifts reflect real generalization, not sampling artifacts.

Each task's raw pool lives in <task>/data/<data_file>; the splits are
written alongside as <task>/data/{train,valid,test}.json (serialized
secretagent Datasets, with prompt_0shot baked into each Case).

Usage:
    cd benchmarks/natural_plan
    uv run python data/partition.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable

_DATA_DIR = Path(__file__).resolve().parent
_BENCHMARK_DIR = _DATA_DIR.parent
_SECRETAGENT_ROOT = _BENCHMARK_DIR.parent.parent

sys.path.insert(0, str(_SECRETAGENT_ROOT / 'src'))

from secretagent.dataset import Dataset, Case


# -- Task configs --

TASKS = {
    'calendar': {
        'data_file': 'calendar_scheduling.json',
        'strata_key': lambda inst: f"({inst['num_people']},{inst['num_days']})",
        'prompt_field': 'prompt_0shot',
    },
    'meeting': {
        'data_file': 'meeting_planning.json',
        'strata_key': lambda inst: str(inst['num_people']),
        'prompt_field': 'prompt_0shot',
    },
    'trip': {
        'data_file': 'trip_planning.json',
        'strata_key': lambda inst: str(inst['num_cities']),
        'prompt_field': 'prompt_0shot',
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


def save_dataset(filepath: Path, task: str, split: str, cases: list[Case]):
    dataset = Dataset(
        name=f'naturalplan_{task}',
        split=split,
        cases=cases,
    )
    filepath.write_text(dataset.model_dump_json(indent=2))
    print(f'  {filepath}: {len(cases)} cases')


def partition_task(task: str, cfg: dict):
    task_data_dir = _BENCHMARK_DIR / task / 'data'
    with open(task_data_dir / cfg['data_file']) as f:
        all_data = json.load(f)

    print(f'{task}: {len(all_data)} total examples')

    # All three splits: stratified, disjoint, different seeds.
    used_keys: set[str] = set()
    for split_name, split_cfg in SPLITS.items():
        available = {k: v for k, v in all_data.items() if k not in used_keys}
        sampled = stratified_sample(
            available, cfg['strata_key'], split_cfg['n'], split_cfg['seed'],
        )
        used_keys.update(sampled.keys())
        cases = make_cases(sampled, cfg['prompt_field'])
        save_dataset(task_data_dir / f'{split_name}.json', task, split_name, cases)


if __name__ == '__main__':
    for task, cfg in TASKS.items():
        partition_task(task, cfg)
    print('\nDone. {train,valid,test}.json written per task (100 each, stratified, disjoint).')
    print('  train = stratified seed=42, valid = stratified seed=43, test = stratified seed=44')
