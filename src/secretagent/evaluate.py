"""Support for evaluating agents on Datasets.
"""

from abc import ABC, abstractmethod
import datetime
import json
import pandas as pd
from pathlib import Path
import os
from tqdm import tqdm
from typing import Any

from secretagent import config, record
from secretagent.dataset import Case, Dataset
from secretagent.core import Interface


class Evaluator(ABC):
    """Abstract class for measuring performance on a dataset.
    """

    @abstractmethod
    def compare_predictions(
            self, predicted_output: Any, expected_output: Any 
    ) -> dict[str, Any]:
        """Compare the predicted_output and expected_output.

        Outputs a dictionary with one or more metrics for the case,
        like {'correct': 1}.
        """
        ...

    def measure(self, example: Case, interface: Interface) -> dict[str, Any]:
        """Measure performance on a case.
        """
        # record a run
        with record.recorder() as records:
            predicted_output = interface(*example.input_args)
            llm_usage_stats = self.aggregate_usage_stats(records)
        # compute the dataset-dependent metrics
        metrics = self.compare_predictions(
            predicted_output, example.expected_output)
        # merge all the metrics and records together
        return dict(
            predicted_output=predicted_output,
            expected_output=example.expected_output,
            **metrics,
            **llm_usage_stats)

    def aggregate_usage_stats(self, records: list[dict[str,Any]]) -> list[dict[str, Any]]:
        """Given a recorder - sum the usage statistics passed out from llm_util.

        The 'records' list should be created by 'with record.recorder
        recorder() as rec', which means that it will have a 'stats'
        key storing the llm_util statistics.  This is normally used as
        a helper function for measure().
        """
        result = {}
        for record in records:
            for key, value in record['stats'].items():
                result[key] = result.get(key, 0.0) + value
        return result

    def evaluate(self, dataset: Dataset, interface: Interface) -> list[dict[str, Any]]:
        """Compute and save measurements for a dataset.

        If 'evaluate.result_dir' is configured, then a directory
        summarizing the experiment, including the current config and a
        csv file with the measurements for each example.  The info in
        the csv file is also written out incrementally as a jsonl file.
        """
        expt_name = config.get('evaluate.expt_name','**unnamed_expt**')
        result_dir = config.get('evaluate.result_dir')
        if not result_dir:
            results = []
            for example in tqdm(dataset.cases):
                result = self.measure(example, interface)
                results.append(dict(expt_name=expt_name, **result))
        else:
            # generate new directory
            timestamp = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
            filestem = f'{timestamp}.{expt_name}'
            dirname = Path(result_dir) / filestem
            os.makedirs(dirname, exist_ok=True)

            # write out the current config 
            config.save(dirname / 'config.yaml')
            print(f'config saved in {dirname}/config.yaml')

            # save the results as they come in into a jsonl file,
            # we we can monitor progress as we go
            with open(dirname / 'results.jsonl', 'w') as fp:
                results = []
                for example in tqdm(dataset.cases):
                    result = self.measure(example, interface)
                    row = dict(expt_name=expt_name, **result)
                    results.append(row)
                    fp.write(json.dumps(row) + '\n')

            # also save the full set of results as a CSV to load in
            # later
            df = pd.DataFrame(results)
            df.to_csv(dirname / 'results.csv')
            print(f'saved in {dirname}/results.csv')

        return results
