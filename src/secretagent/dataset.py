"""Support for evaluation of Interfaces on data.
"""

from __future__ import annotations # forward references

import datetime
from pydantic import BaseModel
from typing import Any, Optional

from secretagent.core import Interface


class Case(BaseModel):
    """A single test case.
    """
    name: str
    metadata: Optional[dict[str,Any]] = None
    input_args: Optional[Any] = None
    input_kw: Optional[Any] = None
    expected_output: Optional[Any] = None
    
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
