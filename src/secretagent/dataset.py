"""Support for evaluation of Interfaces on data.
"""

from __future__ import annotations # forward references

import random

from pydantic import BaseModel
from typing import Any, Callable, Optional


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
        """Drop all but first n instances.

        Returns self, after modification, to support chaining.
        """
        self.cases = self.cases[:n]
        print(f'Discarded all but first {n} cases')
        return self

    def tail(self, n: int) -> Dataset:
        """Drop the first n instances.

        Returns self, after modification, to support chaining.
        """
        self.cases = self.cases[n:]
        print(f'Discarded first {len(self.cases)} cases')
        return self

    def shuffle(self, seed: int | None) -> Dataset:
        """Shuffle the examples.

        Returns self, after modification, to support chaining.
        """
        if seed is not None:
            rng = random.Random(seed)
            rng.shuffle(self.cases)
            print(f'Shuffled with seed {seed}')
        return self

    def stratified_sample(self, n: int, key: Callable[[Case], str],
                          seed: int = 42) -> Dataset:
        """Draw a stratified sample of n cases, preserving proportions of key(case).

        Uses largest-remainder method: each group gets at least 1 representative
        (if n >= num_groups). Returns a new Dataset.
        """
        groups: dict[str, list[Case]] = {}
        rng = random.Random(seed)
        for case in self.cases:
            k = key(case)
            groups.setdefault(k, []).append(case)
        for items in groups.values():
            rng.shuffle(items)

        if n >= len(self.cases):
            result = list(self.cases)
            rng.shuffle(result)
            return Dataset(name=self.name, split=self.split, metadata=self.metadata, cases=result)

        if n < len(groups):
            flat = list(self.cases)
            rng.shuffle(flat)
            return Dataset(name=self.name, split=self.split, metadata=self.metadata, cases=flat[:n])

        # Largest-remainder allocation
        total = len(self.cases)
        exact = {name: len(items) * n / total for name, items in groups.items()}
        allocs = {name: max(int(e), 1) for name, e in exact.items()}
        allocated = sum(allocs.values())
        remaining = n - allocated

        if remaining > 0:
            remainders = sorted(groups.keys(), key=lambda nm: exact[nm] - allocs[nm], reverse=True)
            for nm in remainders:
                if remaining <= 0:
                    break
                if allocs[nm] < len(groups[nm]):
                    allocs[nm] += 1
                    remaining -= 1
        elif remaining < 0:
            trimmable = sorted([nm for nm in groups if allocs[nm] > 1],
                              key=lambda nm: allocs[nm], reverse=True)
            for nm in trimmable:
                if remaining >= 0:
                    break
                allocs[nm] -= 1
                remaining += 1

        selected = []
        for nm, items in groups.items():
            selected.extend(items[:allocs[nm]])
        rng.shuffle(selected)

        return Dataset(name=self.name, split=self.split, metadata=self.metadata, cases=selected)

    def configure(self, shuffle_seed: int | None = None, n: int | None = None):
        """Configure by shuffling and subsetting the dataset.

        Returns self, after modification, to support chaining.
        """
        if shuffle_seed is not None:
            self.shuffle(shuffle_seed)
        if n is not None:
            self.head(n)
        return self
