"""Support for evaluating agents on Datasets.
"""

from abc import ABC, abstractmethod
import json
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from typing import Any, Iterator
import warnings

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

        If an exception was raised in making the prediction,
        predicted_output will be a string starting with '**exception
        raised**'
        """
        ...

    def measure(self, example: Case, interface: Interface) -> dict[str, Any]:
        """Measure performance on a case.

        If evaluate.record_details is True, includes the full rollout
        (recorder output) under the 'rollout' key.
        """
        # record a run
        with record.recorder() as records:
            try:
                predicted_output = interface(*example.input_args)  # type: ignore[misc]
            except Exception as ex:
                predicted_output = f'**exception raised**: {ex}'
        llm_usage_stats = self.aggregate_usage_stats(records)
        # compute the dataset-dependent metrics
        metrics = self.compare_predictions(
            predicted_output, example.expected_output)
        # merge all the metrics and records together
        result = dict(
            predicted_output=predicted_output,
            expected_output=example.expected_output,
            **metrics,
            **llm_usage_stats)
        if config.get('evaluate.record_details'):
            result['rollout'] = records
        return result

    def aggregate_usage_stats(self, records: list[dict[str,Any]]) -> dict[str, Any]:
        """Given a recorder - sum the usage statistics passed out from llm_util.

        The 'records' list should be created by 'with record.recorder
        recorder() as rec', which means that it will have a 'stats'
        key storing the llm_util statistics.  This is normally used as
        a helper function for measure().
        """
        result: dict[str, float] = {}
        for rec in records:
            for key, value in rec['stats'].items():
                if isinstance(value, (int, float)):
                    result[key] = result.get(key, 0.0) + value
        return result

    def measurements(self, dataset: Dataset, interface: Interface) -> Iterator[dict[str, Any]]:
        max_workers = int(config.get('evaluate.max_workers', 1))
        if max_workers <= 1:
            for example in tqdm(dataset.cases):
                row = self.measure(example, interface)
                row['case_name'] = example.name
                yield row
        else:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            def _run(ex):
                row = self.measure(ex, interface)
                row['case_name'] = ex.name
                return row
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_run, ex): ex for ex in dataset.cases}
                for fut in tqdm(as_completed(futures), total=len(futures)):
                    yield fut.result()
            

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
                try:
                    fp.write(json.dumps(row, default=str) + '\n')
                    results.append(row)
                except TypeError:
                    warnings.warn(f'discarded row that cannot be serialized {row}')

        # also save as CSV for easy loading (drop rollout column if present)
        csv_rows = [
            {k: v for k, v in row.items() if k != 'rollout'}
            for row in results
        ]
        df = pd.DataFrame(csv_rows).set_index('case_name')
        df.to_csv(csv_path)
        print(f'saved in {csv_path}')
        return csv_path


class ExactMatchEvaluator(Evaluator):
    """Evaluator that scores 1.0 for exact match, 0.0 otherwise."""

    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        return dict(correct=float(predicted_output == expected_output))
