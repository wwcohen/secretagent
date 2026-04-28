"""NbaEvaluator: binary verdict scoring.

Produces two metrics per case:
  correct      - 1.0 if bool(predicted) == bool(expected)
  failure_mode - "none" | "calculation_error" | "extraction_failure" | "step_limit"

The primary metric (correct) is binary because NBA answers are True/False
(violation / compliant). Both predicted and expected are converted through
float → bool before comparison, so any truthy prediction matches a True
ground truth.

failure_mode distinguishes react's step-limit exhaustion from generic
pipeline exceptions, since the former is a characteristic failure mode
of tool-using agents and worth reporting separately.

NOTE: The retry-exhausted path at evaluate.py:104-107 constructs rows
directly with 'predicted_output': None and 'correct': 0, bypassing
compare_predictions entirely. Rows from that path therefore lack a
failure_mode field. Aggregation code should treat missing failure_mode
as either its own category or default to 'extraction_failure'.
"""

from typing import Any

from secretagent.evaluate import Evaluator


_STEP_LIMIT_PATTERNS = (
    "usagelimit",
    "usage limit",
    "exceeded the maximum",
    "maximum number of",
    "max_iterations",
)


def _verdict_match(predicted: Any, expected: Any) -> bool:
    """True if bool(predicted) == bool(expected).

    Both values are converted through float first to handle string
    representations ("1.0", "0.0", "True", "False").
    """
    try:
        p = bool(float(predicted))
        e = bool(float(expected))
    except (TypeError, ValueError):
        return False
    return p == e


class NbaEvaluator(Evaluator):
    """Binary verdict scoring for NBA CBA compliance predictions.

    Primary metric `correct` is exact bool match. `failure_mode`
    classifies non-correct predictions into actionable categories.
    """

    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        if predicted_output is None:
            return dict(correct=0.0, failure_mode="calculation_error")

        if isinstance(predicted_output, str) and predicted_output.startswith("**exception raised**"):
            lower = predicted_output.lower()
            if any(pat in lower for pat in _STEP_LIMIT_PATTERNS):
                failure_mode = "step_limit"
            else:
                failure_mode = "extraction_failure"
            return dict(correct=0.0, failure_mode=failure_mode)

        correct = float(_verdict_match(predicted_output, expected_output))
        failure_mode = "none" if correct else "calculation_error"
        return dict(correct=correct, failure_mode=failure_mode)
