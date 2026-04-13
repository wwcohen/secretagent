"""Population manager for population-based pipeline optimization."""

from __future__ import annotations

import logging
import random
from typing import Any

from pydantic import BaseModel

from secretagent.orchestrate.pipeline import Pipeline
from secretagent.orchestrate.profiler import PipelineProfile

log = logging.getLogger(__name__)


class PipelineCandidate(BaseModel):
    """A single candidate in the population."""
    model_config = {'arbitrary_types_allowed': True}

    pipeline: Pipeline
    config: dict[str, Any] = {}
    profile: PipelineProfile | None = None
    instance_scores: dict[str, float] = {}
    generation: int = 0
    parent_index: int | None = None
    mutation_history: list[str] = []

    @property
    def accuracy(self) -> float:
        if self.profile:
            return self.profile.accuracy
        if self.instance_scores:
            scores = list(self.instance_scores.values())
            return sum(scores) / len(scores) if scores else 0.0
        return 0.0

    @property
    def avg_cost(self) -> float:
        if self.profile:
            return self.profile.avg_cost
        return 0.0


class Population:
    """Manages a population of pipeline candidates.

    Supports two seeding strategies:
    - compose_n: generate N independent compositions
    - compose_then_mutate: compose 1, then mutate to fill population
    """

    def __init__(self, population_size: int = 5, seed_strategy: str = 'compose_then_mutate'):
        if seed_strategy not in ('compose_n', 'compose_then_mutate'):
            raise ValueError(f'unknown seed strategy: {seed_strategy!r}')
        self.population_size = population_size
        self.seed_strategy = seed_strategy
        self.candidates: list[PipelineCandidate] = []
        self._generation = 0

    @property
    def generation(self) -> int:
        return self._generation

    def add(self, candidate: PipelineCandidate) -> int:
        """Add a candidate, return its index."""
        self.candidates.append(candidate)
        return len(self.candidates) - 1

    def remove(self, index: int) -> None:
        """Remove candidate at index."""
        if 0 <= index < len(self.candidates):
            self.candidates.pop(index)

    def best(self) -> PipelineCandidate | None:
        """Return candidate with highest aggregate accuracy."""
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.accuracy)

    def pareto_front(self, metric_key: str = 'correct') -> list[int]:
        """Return indices of instance-wise Pareto-optimal candidates.

        A candidate is on the Pareto front if it is the best performer
        on at least one example in instance_scores.
        """
        if not self.candidates:
            return []

        # Collect all case names across candidates
        all_cases = set()
        for c in self.candidates:
            all_cases.update(c.instance_scores.keys())

        if not all_cases:
            # No instance scores: return all candidates
            return list(range(len(self.candidates)))

        # A candidate is Pareto-optimal if it's best on at least one case
        front_indices: set[int] = set()
        for case in all_cases:
            best_score = -1.0
            best_idx = -1
            for i, c in enumerate(self.candidates):
                score = c.instance_scores.get(case, 0.0)
                if score > best_score:
                    best_score = score
                    best_idx = i
            if best_idx >= 0:
                front_indices.add(best_idx)

        return sorted(front_indices)

    def advance_generation(self) -> None:
        """Increment generation counter."""
        self._generation += 1

    def summary(self) -> str:
        """Human-readable population summary for meta-optimizer prompts."""
        lines = [
            f'Population: {len(self.candidates)} candidates, generation {self._generation}',
            '',
        ]
        front = self.pareto_front()
        for i, c in enumerate(self.candidates):
            on_front = '*' if i in front else ' '
            mutations = ' → '.join(c.mutation_history) if c.mutation_history else 'seed'
            lines.append(
                f'  [{on_front}] #{i}: accuracy={c.accuracy:.1%}, '
                f'avg_cost=${c.avg_cost:.4f}, gen={c.generation}, '
                f'history=[{mutations}]'
            )
        lines.append('')
        lines.append(f'Pareto front: {front}')
        return '\n'.join(lines)
