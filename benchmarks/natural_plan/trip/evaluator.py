"""No-arg evaluator for the NaturalPlan trip-planning task.

Used by the generic runner, e.g.::

    uv run python -m secretagent.cli.expt run --config conf/trip.yaml \
      --evaluator evaluator.TripEvaluator

Trace info (full rollouts) is captured by setting
``evaluate.record_details=true``; the base Evaluator writes it into
results.jsonl.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # for eval_utils

from secretagent.evaluate import Evaluator
from eval_utils import eval_trip_single


class TripEvaluator(Evaluator):
    def compare_predictions(self, predicted_output, expected_output):
        pred = str(predicted_output) if predicted_output is not None else ''
        return dict(correct=eval_trip_single(pred, expected_output))
