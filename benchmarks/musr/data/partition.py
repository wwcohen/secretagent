"""Partition MUSR datasets into train/val/test splits.

Usage:
    uv run python data/partition.py

Creates {split}_train.json, {split}_val.json, {split}_test.json
with 75/75/100 examples each (shuffled with seed 42).
"""

import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent
SEED = 42
TRAIN_N = 75
VAL_N = 75
# TEST_N = remainder

SPLITS = ['murder_mysteries', 'object_placements', 'team_allocation']


def partition(split: str):
    with open(DATA_DIR / f'{split}.json') as f:
        data = json.load(f)

    examples = data['examples']
    rng = random.Random(SEED)
    rng.shuffle(examples)

    train = examples[:TRAIN_N]
    val = examples[TRAIN_N:TRAIN_N + VAL_N]
    test = examples[TRAIN_N + VAL_N:]

    for name, subset in [('train', train), ('val', val), ('test', test)]:
        out = {**data, 'examples': subset}
        out_path = DATA_DIR / f'{split}_{name}.json'
        with open(out_path, 'w') as f:
            json.dump(out, f, indent=2)
        print(f'{split}_{name}: {len(subset)} examples -> {out_path.name}')


if __name__ == '__main__':
    for split in SPLITS:
        partition(split)
        print()
