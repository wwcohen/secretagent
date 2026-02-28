import json
import re

from pathlib import Path
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EqualsExpected

def load(split: str) -> Dataset:
    def example_as_case(index, example):
        return Case(
            name=f'ex{index:03d}',
            inputs=re.search(r'"([^"]*)"', example['input']).group(1),
            expected_output=(example['target']=="yes")
        )
    json_file = Path(__file__).parent / 'data' / f'{split}.json'
    with open(json_file) as fp:
        data = json.load(fp)
        examples = data['examples']
        return Dataset(
            cases=[
                example_as_case(i, ex)
                for i, ex in enumerate(examples)],
            evaluators=[EqualsExpected()]
        )


if __name__ == '__main__':
    dataset = load('valid')
    report = dataset.evaluate_sync(lambda text: True)
    print(report.averages())
    report = dataset.evaluate_sync(lambda text: False)
    print(report.averages())

    
