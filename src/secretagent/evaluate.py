from abc import ABC, abstractmethod
import datetime
import pandas as pd
from pathlib import Path
import os
from tqdm import tqdm
from typing import Any

from secretagent import config
from secretagent.dataset import Case, Dataset
from secretagent.core import Interface


class Evaluator(ABC):
    """Abstract class for measuring performance on a dataset.
    """

    @abstractmethod
    def measure(example: Case, interface: Interface) -> dict[str, Any]:
        """Run the implemented interface and measure performance.
        """
        ...

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
        """Save the measurements for a dataset.
        """
        expt_name = config.get('evaluate.expt_name','**unnamed_expt**')
        results = []
        for example in tqdm(dataset.cases):
            result = self.measure(example, interface)
            results.append(dict(expt_name=expt_name, **result))

        if result_dir := config.get('evaluate.result_dir'):
            timestamp = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
            filestem = f'{timestamp}.{expt_name}'
            dirname = Path(result_dir) / filestem
            os.makedirs(dirname, exist_ok=True)
            df = pd.DataFrame(results)
            df.to_csv(dirname / 'results.csv')
            config.save(dirname / 'config.yaml')
            print(f'saved in {dirname}/results.csv')
        
        return results
