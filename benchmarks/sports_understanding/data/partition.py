"""partition data.json into train/valid/test
"""

import json
import random

def save_data(filename, canary, examples):
    obj = dict(canary=canary, examples=examples)
    with open(filename, 'w') as fp:
        json.dump(obj, fp, indent=2)
    print(f'wrote {len(examples)} to {filename}')


if __name__ == '__main__':
    with open('data.json') as fp:
        data = json.load(fp)
        canary = data['canary']
        examples = data['examples']
        random.seed(137)
        random.shuffle(examples)
        save_data('test.json', canary, examples[:100])
        save_data('train.json', canary, examples[100:175])
        save_data('valid.json', canary, examples[175:])
