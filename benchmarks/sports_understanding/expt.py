import json
from pathlib import Path
import re
from typing import Any

from secretagent.record import recorder
from secretagent.core import Interface
from secretagent.dataset import Dataset, Case, Evaluator
import tools

class ExptEvaluator(Evaluator):

    def measure(self, example: Case, interface: Interface) -> dict[str, Any]:
        with recorder() as rec:
            result = tools.sports_understanding(*example.input_args)
            STOPPED HERE

def load_dataset(split: str) -> Dataset:
    def example_as_case(index, example):
        return Case(
            name=f'ex{index:03d}',
            input_args=(re.search(r'"([^"]*)"', example['input']).group(1),),
            expected_output=(example['target']=="yes")
        )
    json_file = Path(__file__).parent / 'data' / f'{split}.json'
    with open(json_file) as fp:
        data = json.load(fp)
        examples = data['examples']
        return Dataset(
            name='sports_understanding',
            split=split,
            cases=[
                example_as_case(i, ex)
                for i, ex in enumerate(examples)
            ],
        )


if __name__ == '__main__':
    dataset = load_dataset('valid')
    dataset.head(4)
    print('dataset is', dataset.summary())
    
    tools.analyze_sentence.implement_via('simulate')
    tools.sport_for.implement_via('simulate')
    tools.consistent_sports.implement_via('simulate')
    
