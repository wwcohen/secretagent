"""Partition each MUSR Dataset JSON file into train/val/test splits.

Reads ``<task>/data/<split>.json`` (produced by ``download.py``) and writes
``<task>/data/<split>_train.json``, ``<split>_val.json``, ``<split>_test.json``
with 75 / 75 / remainder cases each (shuffled with seed 42).

Usage (from repo root):
    uv run python benchmarks/musr/data/partition.py
"""

import json
import random
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
SEED = 42
TRAIN_N = 75
VAL_N = 75
# TEST_N = remainder

# (huggingface split name, task subdir name)
SPLITS = [
    ("murder_mysteries",  "murder"),
    ("object_placements", "object"),
    ("team_allocation",   "team"),
]


def partition(split: str, task: str):
    in_path = BENCHMARK_DIR / task / "data" / f"{split}.json"
    with open(in_path) as f:
        data = json.load(f)

    cases = list(data["cases"])
    rng = random.Random(SEED)
    rng.shuffle(cases)

    parts = [
        ("train", cases[:TRAIN_N]),
        ("val",   cases[TRAIN_N:TRAIN_N + VAL_N]),
        ("test",  cases[TRAIN_N + VAL_N:]),
    ]

    for name, subset in parts:
        out_split = f"{split}_{name}"
        out = {**data, "split": out_split, "cases": subset}
        out_path = BENCHMARK_DIR / task / "data" / f"{out_split}.json"
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"{out_split}: {len(subset)} cases -> {out_path}")


if __name__ == "__main__":
    for split, task in SPLITS:
        partition(split, task)
        print()
