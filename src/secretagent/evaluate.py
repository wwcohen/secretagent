"""Support for evaluating agents on Datasets.
"""

from abc import ABC, abstractmethod
import json
import os
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from typing import Any, Iterator

from secretagent import config, record, savefile
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

    def measurements(self, dataset: Dataset, interface: Interface) -> Iterator[dict[str, Any]]:
        for example in tqdm(dataset.cases):
            row = self.measure(example, interface)
            row['case_name'] = example.name
            yield row

    def evaluate(self, dataset: Dataset, interface: Interface) -> Path:
        """Compute and save measurements for a dataset.

        Results are put in csv format into a savefile.  Returns the
        path to the csv file.
        """
        expt_name = config.get('evaluate.expt_name')
        result_dir = config.require('evaluate.result_dir')
        csv_path, jsonl_path = savefile.filename_list(
            result_dir, ['results.csv', 'results.jsonl'], file_under=expt_name)
        # save results incrementally as jsonl so we can monitor progress
        with open(jsonl_path, 'w') as fp:
            results = []
            for row in self.measurements(dataset, interface):
                row.update(expt_name=expt_name)
                results.append(row)
                fp.write(json.dumps(row) + '\n')
        # also save as CSV for easy loading
        df = pd.DataFrame(results).set_index('case_name')
        df.to_csv(csv_path)
        print(f'saved in {csv_path}')
        return csv_path
