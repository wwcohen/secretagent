"""Support for evaluation of Interfaces on data.
"""

from __future__ import annotations # forward references

from abc import ABC, abstractmethod

import datetime
import os
import pandas as pd
from pathlib import Path
from pydantic import BaseModel
from tqdm import tqdm
from typing import Any, Optional

from secretagent import config
from secretagent.core import Interface


class Case(BaseModel):
    """A single test case.
    """
    name: str
    metadata: Optional[dict[str,Any]] = None
    input_args: Optional[Any] = None
    input_kw: Optional[Any] = None
    expected_output: Optional[Any] = None
    
class Evaluator(ABC):
    """A way of measuring performance on a case.
    """

    @abstractmethod
    def measure(example: Case, interface: Interface) -> dict[str, Any]:
        """Run the implemented interface and measure performance.
        """
        ...

    def evaluate(dataset: Dataset, interface: Interface) -> list[dict[str, Any]]:
        expt_name = config.get('expt_name','**unnamed_expt**')
        results = []
        for example in tqdm(dataset.cases):
            result = self.measure(example, interface)
            results.append(expt_name=expt_name, **result)

        if result_dir := config.get('result_dir'):

            timestamp = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
            filestem = f'{timestamp}.{expt_name}'
            dirname = Path(config.get('result_dir') / filestem)
            os.makedirs(dirname, exist_ok=True)

            df = pd.DataFrame(results)
            df.to_csv(Path(result_dir) /  'results.csv')
            config.save(Path(result_dir) / 'config.yaml')

        print(f'saved in {result_dir}/results.csv')
        

class Dataset(BaseModel):
    """A list of cases plus a little meta information.
    """
    name: str
    split: Optional[str] = None
    metadata: Optional[dict[str,Any]] = None
    cases: list[Case]
    
    def summary(self):
        return f'name={self.name} split={self.split} size={len(self.cases)}'

    def head(self, n: int) -> Dataset:
        """Drop all but first n instances."""
        self.cases = self.cases[:n]
        print(f'Discarded all but first {n} cases')
        return self

    def tail(self, n: int) -> Dataset:
        """Drop the first n instances."""
        self.cases = self.cases[n:]
        print(f'Discarded first {len(self.cases)} cases')
        return self

    def shuffle(self, seed: int | None) -> Dataset:
        """Shuffle the examples."""
        if seed is not None:
            rng = random.Random(seed)
            rng.shuffle(self.cases)
            print(f'Shuffled with seed {seed}')
        return self
