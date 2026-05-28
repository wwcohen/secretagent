"""Convert raw TabMWP problems_{split}.json files into json-serialized
Datasets at {split}.json. Run after data/download.py.

Each Case embeds the table data (table_for_pd, table_title, table) in
metadata so the dataset is self-contained — the table store can be
populated from the Dataset at runtime via the conf's
dataset.setup_hook: ptools.load_table_store.

Maps raw split names: dev -> val, dev1k -> val1k, test/test1k/train
unchanged.
"""

import json
from pathlib import Path

from secretagent.dataset import Dataset, Case


_RAW_TO_OUT = {
    'problems_train.json': 'train',
    'problems_dev.json': 'val',
    'problems_test.json': 'test',
    'problems_dev1k.json': 'val1k',
    'problems_test1k.json': 'test1k',
}


def example_as_case(ex_id, ex):
    return Case(
        name=ex_id,
        input_args=(ex['question'], ex['table'], ex_id, ex['choices']),
        expected_output=str(ex['answer']),
        metadata={
            'ques_type': ex.get('ques_type'),
            'ans_type': ex.get('ans_type'),
            'grade': ex.get('grade'),
            'table': ex.get('table'),
            'table_for_pd': ex.get('table_for_pd'),
            'table_title': ex.get('table_title'),
        },
    )


def save_dataset(filename, split, raw):
    dataset = Dataset(
        name='tabmwp',
        split=split,
        cases=[example_as_case(ex_id, ex) for ex_id, ex in raw.items()],
    )
    with open(filename, 'w', encoding='utf-8') as fp:
        fp.write(dataset.model_dump_json(indent=2))
    print(f'wrote {len(raw)} cases to {filename}')


if __name__ == '__main__':
    here = Path(__file__).parent
    for raw_name, out_split in _RAW_TO_OUT.items():
        src = here / raw_name
        if not src.exists():
            print(f'skipping {raw_name} (not downloaded; run download.py first)')
            continue
        with open(src, encoding='utf-8') as fp:
            raw = json.load(fp)
        save_dataset(here / f'{out_split}.json', out_split, raw)
