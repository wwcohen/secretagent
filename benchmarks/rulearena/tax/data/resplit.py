"""Reshuffle tax source jsonl files to target sizes with stratified balance.

Pools existing train/valid/test jsonl records and redistributes them into
new splits matching prof's targets: 100 test / 150 train / 50 valid
(test=100, train:valid=3:1 of remaining).
Uses a true stratified allocation (largest-remainder variant) so per-level
counts within each split are balanced within 1 case.

After running:
    uv run python data/partition.py
to regenerate Dataset-format .json files.

Run from tax/:
    uv run python data/resplit.py
"""

import json
import random
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent
SEED = 137  # matches dataset.shuffle_seed in conf.yaml (independent use, same value)
TARGETS = {"test": 100, "train": 150, "valid": 50}


def stratified_allocation(level_sizes: dict[int, int], targets: dict[str, int]) -> dict[tuple[str, int], int]:
    """Return alloc[(split, level)] = count such that:
      - For each level: sum over splits == level_sizes[level]  (no records lost)
      - For each split: sum over levels == targets[split]      (exact target sum)

    Algorithm: floor allocation via proportional share, then distribute each
    level's unassigned records to the split with the largest remaining shortfall.
    Deterministic given the input dicts' iteration order.
    """
    total = sum(level_sizes.values())
    if total != sum(targets.values()):
        raise ValueError(f"level_sizes sum {total} != targets sum {sum(targets.values())}")

    alloc = {
        (split, lv): int(targets[split] * level_sizes[lv] / total)
        for split in targets
        for lv in level_sizes
    }
    level_extra = {
        lv: level_sizes[lv] - sum(alloc[(s, lv)] for s in targets)
        for lv in level_sizes
    }
    split_extra = {
        s: targets[s] - sum(alloc[(s, lv)] for lv in level_sizes)
        for s in targets
    }

    for lv in list(level_extra):
        while level_extra[lv] > 0:
            needy = max(split_extra, key=split_extra.get)
            if split_extra[needy] <= 0:
                break
            alloc[(needy, lv)] += 1
            level_extra[lv] -= 1
            split_extra[needy] -= 1
    return alloc


def main():
    # Pool source records
    all_records = []
    for split in ("train", "valid", "test"):
        path = DATA / f"{split}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing; cannot pool")
        with path.open(encoding="utf-8") as f:
            all_records.extend(json.loads(line) for line in f)
    total = len(all_records)
    target_sum = sum(TARGETS.values())
    print(f"Pooled {total} records from existing jsonl files")
    if total != target_sum:
        raise RuntimeError(f"pooled total {total} != target sum {target_sum}")

    # Group by level, shuffle each group deterministically
    by_level: dict[int, list] = defaultdict(list)
    for r in all_records:
        by_level[r["level"]].append(r)
    print("Source per-level counts:", {lv: len(rs) for lv, rs in sorted(by_level.items())})

    rng = random.Random(SEED)
    for lv in sorted(by_level):
        rng.shuffle(by_level[lv])

    # Stratified allocation
    level_sizes = {lv: len(rs) for lv, rs in by_level.items()}
    alloc = stratified_allocation(level_sizes, TARGETS)
    print("Allocation per (split, level):", {f"{s}_l{lv}": alloc[(s, lv)] for s in TARGETS for lv in sorted(level_sizes)})

    # Carve per level per split
    new_splits: dict[str, list] = {s: [] for s in TARGETS}
    for lv in sorted(by_level):
        records = by_level[lv]
        cursor = 0
        for s in ("test", "train", "valid"):
            n = alloc[(s, lv)]
            new_splits[s].extend(records[cursor:cursor + n])
            cursor += n

    # Write new jsonl files (overwrites; source is regenerable from upstream repo)
    for split in ("train", "valid", "test"):
        records = new_splits[split]
        path = DATA / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        per_level: dict[int, int] = defaultdict(int)
        for r in records:
            per_level[r["level"]] += 1
        detail = ", ".join(f"l{lv}: {per_level[lv]}" for lv in sorted(per_level))
        print(f"Wrote {path.name}: {len(records)} cases [{detail}]")


if __name__ == "__main__":
    main()
