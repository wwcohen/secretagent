"""One-time data preparation script.

Reads from a RuleArena repository clone, splits each domain+level into
train/valid/test (60/20/20 within each complexity level — Option A), and
writes self-contained JSONL files to data/{domain}/{split}.jsonl.

Also vendors:
  - Rules text files into data/{domain}/
  - Airline fee tables (8 CSVs) into data/airline/fee_tables/
  - Tax Python modules into data/tax/

After running this script external/RuleArena is no longer needed at
runtime.

Usage:
    uv run python data/prepare.py /path/to/RuleArena
    uv run python data/prepare.py ../../../RuleArena
"""

import argparse
import json
import random
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).parent


def split_examples(examples: list, seed: int = 137) -> tuple[list, list, list]:
    """Split examples 60/20/20 train/valid/test using a fixed seed."""
    rng = random.Random(seed)
    shuffled = list(examples)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * 0.6)
    n_valid = int(n * 0.2)
    train = shuffled[:n_train]
    valid = shuffled[n_train:n_train + n_valid]
    test  = shuffled[n_train + n_valid:]
    return train, valid, test


def write_splits(out_dir: Path, splits: dict[str, list]):
    for split_name, records in splits.items():
        out_path = out_dir / f'{split_name}.jsonl'
        with open(out_path, 'w', encoding='utf-8') as f:
            for rec in records:
                f.write(json.dumps(rec) + '\n')
        print(f'  {split_name:6s}: {len(records):4d} records -> {out_path.name}')


def prepare_airline(rulearena_path: Path):
    print('airline:')
    out_dir = DATA_DIR / 'airline'
    out_dir.mkdir(exist_ok=True)

    splits: dict[str, list] = {'train': [], 'valid': [], 'test': []}

    for level in range(3):
        src = rulearena_path / 'airline' / 'synthesized_problems' / f'comp_{level}.jsonl'
        examples = []
        with open(src, encoding='utf-8') as f:
            for orig_idx, line in enumerate(f):
                record = json.loads(line)
                record['level'] = level
                record['orig_idx'] = orig_idx
                examples.append(record)
        train, valid, test = split_examples(examples)
        splits['train'].extend(train)
        splits['valid'].extend(valid)
        splits['test'].extend(test)
        print(f'  level {level}: {len(examples)} -> {len(train)}/{len(valid)}/{len(test)}')

    write_splits(out_dir, splits)

    shutil.copy(
        rulearena_path / 'airline' / 'reference_rules_textual.txt',
        out_dir / 'reference_rules_textual.txt',
    )
    print('  copied reference_rules_textual.txt')

    fee_dst = out_dir / 'fee_tables'
    if fee_dst.exists():
        shutil.rmtree(fee_dst)
    shutil.copytree(rulearena_path / 'airline' / 'fee_tables', fee_dst)
    n_csvs = sum(1 for _ in fee_dst.rglob('*.csv'))
    print(f'  copied fee_tables/ ({n_csvs} CSVs)')


def prepare_nba(rulearena_path: Path):
    print('nba:')
    out_dir = DATA_DIR / 'nba'
    out_dir.mkdir(exist_ok=True)

    splits: dict[str, list] = {'train': [], 'valid': [], 'test': []}

    for level in range(3):
        src = rulearena_path / 'nba' / 'annotated_problems' / f'comp_{level}.json'
        with open(src, encoding='utf-8') as f:
            raw = json.load(f)
        examples = []
        for orig_idx, item in enumerate(raw):
            record = dict(item)
            record['level'] = level
            record['orig_idx'] = orig_idx
            examples.append(record)
        train, valid, test = split_examples(examples)
        splits['train'].extend(train)
        splits['valid'].extend(valid)
        splits['test'].extend(test)
        print(f'  level {level}: {len(examples)} -> {len(train)}/{len(valid)}/{len(test)}')

    write_splits(out_dir, splits)

    shutil.copy(
        rulearena_path / 'nba' / 'reference_rules.txt',
        out_dir / 'reference_rules.txt',
    )
    print('  copied reference_rules.txt')


def prepare_tax(rulearena_path: Path):
    print('tax:')
    out_dir = DATA_DIR / 'tax'
    out_dir.mkdir(exist_ok=True)

    splits: dict[str, list] = {'train': [], 'valid': [], 'test': []}

    for level in range(3):
        src = rulearena_path / 'tax' / 'synthesized_problems' / f'comp_{level}.json'
        with open(src, encoding='utf-8') as f:
            raw = json.load(f)
        examples = []
        for orig_idx, item in enumerate(raw):
            record = dict(item)
            record['level'] = level
            record['orig_idx'] = orig_idx
            examples.append(record)
        train, valid, test = split_examples(examples)
        splits['train'].extend(train)
        splits['valid'].extend(valid)
        splits['test'].extend(test)
        print(f'  level {level}: {len(examples)} -> {len(train)}/{len(valid)}/{len(test)}')

    write_splits(out_dir, splits)

    for module in ('prompt.py', 'structured_forms.py', 'micro_evaluation.py'):
        shutil.copy(rulearena_path / 'tax' / module, out_dir / module)
        print(f'  vendored {module}')


def main():
    parser = argparse.ArgumentParser(
        description='Prepare RuleArena data for local use (run once).',
    )
    parser.add_argument(
        'rulearena_path',
        type=Path,
        help='Path to RuleArena repository root (e.g. ../../../RuleArena)',
    )
    args = parser.parse_args()

    rulearena_path = args.rulearena_path.resolve()
    if not rulearena_path.exists():
        raise SystemExit(f'RuleArena path not found: {rulearena_path}')

    print(f'Source : {rulearena_path}')
    print(f'Output : {DATA_DIR}')
    print()

    prepare_airline(rulearena_path)
    print()
    prepare_nba(rulearena_path)
    print()
    prepare_tax(rulearena_path)
    print()
    print('Done. external/RuleArena is no longer needed at runtime.')


if __name__ == '__main__':
    main()
