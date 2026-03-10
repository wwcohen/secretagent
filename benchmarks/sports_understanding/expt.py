import json
import pandas as pd
from pathlib import Path
import re
from typing import Any

from secretagent import record, config
from secretagent.core import Interface
from secretagent.dataset import Dataset, Case
from secretagent.evaluate import Evaluator

import tools

class SportsUnderstandingEvaluator(Evaluator):

    def measure(self, example: Case, interface: Interface) -> dict[str, Any]:
        with record.recorder() as records:
            result = tools.sports_understanding(*example.input_args)
            llm_usage_stats = self.aggregate_usage_stats(records)
            return dict(
                predicted_output=result,
                expected_output=example.expected_output,
                correct=int(result == example.expected_output),
                **llm_usage_stats)

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
    config.configure(llm={'model': "claude-haiku-4-5-20251001"})

    dataset = load_dataset('valid')
    dataset.head(6)
    print('dataset is', dataset.summary())
    
    tools.analyze_sentence.implement_via('simulate')
    tools.sport_for.implement_via('simulate')
    tools.consistent_sports.implement_via('simulate')
    
    evaluator = SportsUnderstandingEvaluator()
    eval_cfg = dict(
        expt_name='workflow_debug',
        result_dir=Path(__file__).parent / 'results'
    )

    with config.configuration(evaluate=eval_cfg):
        result = evaluator.evaluate(dataset, tools.sports_understanding)
        df = pd.DataFrame(result)
    print(df)
