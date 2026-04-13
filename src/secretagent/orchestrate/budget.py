"""Budget tracker for population-based pipeline optimization."""

from __future__ import annotations

import logging
import time
from pydantic import BaseModel

log = logging.getLogger(__name__)


class SpendEvent(BaseModel):
    """A single cost event during optimization."""
    cost: float
    description: str
    timestamp: float  # time.time()


class BudgetTracker:
    """Tracks cumulative optimization cost.

    Modes:
        hard_stop: immediately stop when budget is exhausted
        soft_stop: finish current iteration, then stop
        pareto: continue until Pareto front stops improving (budget is advisory)
    """

    def __init__(self, budget_limit: float, mode: str = 'soft_stop'):
        if mode not in ('hard_stop', 'soft_stop', 'pareto'):
            raise ValueError(f'invalid budget mode: {mode!r}')
        self.budget_limit = budget_limit
        self.mode = mode
        self._events: list[SpendEvent] = []

    def record(self, cost: float, description: str) -> None:
        """Log a spend event."""
        self._events.append(SpendEvent(
            cost=cost, description=description, timestamp=time.time(),
        ))
        log.debug('budget: $%.4f for %s (total: $%.4f / $%.2f)',
                  cost, description, self.total_spent, self.budget_limit)

    @property
    def total_spent(self) -> float:
        return sum(e.cost for e in self._events)

    @property
    def remaining(self) -> float:
        return max(0.0, self.budget_limit - self.total_spent)

    def is_exhausted(self) -> bool:
        """True if total_spent >= budget_limit."""
        return self.total_spent >= self.budget_limit

    def should_stop(self, mid_iteration: bool = False) -> bool:
        """Apply mode logic to decide whether to stop.

        Args:
            mid_iteration: True when called within an iteration (between mutations).
                hard_stop checks mid-iteration, soft_stop only between iterations.
        """
        if self.mode == 'hard_stop':
            return self.is_exhausted()
        elif self.mode == 'soft_stop':
            # soft_stop only triggers between iterations, not mid-iteration
            return self.is_exhausted() and not mid_iteration
        elif self.mode == 'pareto':
            return False
        return False

    def summary(self) -> dict:
        """Summary dict for reporting."""
        return {
            'total_spent': self.total_spent,
            'budget_limit': self.budget_limit,
            'remaining': self.remaining,
            'mode': self.mode,
            'n_events': len(self._events),
            'pct_spent': (self.total_spent / self.budget_limit * 100
                         if self.budget_limit > 0 else 0.0),
        }

    def format_summary(self) -> str:
        """Human-readable summary string."""
        s = self.summary()
        limit_str = f"${s['budget_limit']:.2f}" if s['budget_limit'] < float('inf') else 'unlimited'
        pct_str = f" ({s['pct_spent']:.0f}%)" if s['budget_limit'] < float('inf') else ''
        return f"Budget: ${s['total_spent']:.2f} / {limit_str}{pct_str} [{s['mode']}]"
