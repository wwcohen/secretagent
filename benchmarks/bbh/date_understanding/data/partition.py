"""partition data.json into train/valid/test as json-serialized Datasets
"""

import json
import random

from secretagent.dataset import Dataset, Case


def example_as_case(index, split, example):
    return Case(
        name=f'{split}.{index:03d}',
        input_args=(example['input'],),
        expected_output=example['target'],
    )


def save_dataset(filename, split, canary, examples):
    dataset = Dataset(
        name='date_understanding',
        split=split,
        metadata={'canary': canary},
        cases=[example_as_case(i, split, ex) for i, ex in enumerate(examples)],
    )
    with open(filename, 'w') as fp:
        fp.write(dataset.model_dump_json(indent=2))
    print(f'wrote {len(examples)} to {filename}')


if __name__ == '__main__':
    with open('data.json') as fp:
        data = json.load(fp)
        canary = data['canary']
        examples = data['examples']
        random.seed(137)
        random.shuffle(examples)
        save_dataset('test.json', 'test', canary, examples[:100])
        save_dataset('train.json', 'train', canary, examples[100:175])
        save_dataset('valid.json', 'valid', canary, examples[175:])
