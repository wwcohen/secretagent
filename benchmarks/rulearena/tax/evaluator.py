"""TaxEvaluator: 1%-relative-tolerance scoring with tight-match diagnostic.

Produces three metrics per case:
  correct            - 1.0 if |pred - exp| / |exp| <= 0.01 (1% relative; RuleArena paper)
  correct_tolerance  - 1.0 if math.isclose(pred, exp, rel_tol=1e-5, abs_tol=1e-8) (tight, diagnostic)
  failure_mode       - "none" | "calculation_error" | "extraction_failure" | "step_limit"

The primary metric (correct) uses 1% relative tolerance because that's what
the RuleArena paper reports for tax (tax outputs are non-integer dollars and
small floating-point accumulation in the calculator's chain of arithmetic
can produce tiny offsets that would mask correct reasoning under exact match).
correct_tolerance is the tight diagnostic used to distinguish "exact" from
"close enough" for sensitivity analysis.

Cross-domain note: airline uses correct=exact, correct_tolerance=loose-1%;
tax flips the orientation (correct=1%, correct_tolerance=tight) so the
primary score in each domain matches that domain's paper convention. The
diagnostic column shares a name across domains to keep aggregation code
simple.

failure_mode distinguishes react's step-limit exhaustion from generic
pipeline exceptions, since the former is a characteristic failure mode of
tool-using agents and worth reporting separately.

NOTE: The retry-exhausted path at evaluate.py:104-107 constructs rows
directly with 'predicted_output': None and 'correct': 0, bypassing
compare_predictions entirely. Rows from that path therefore lack a
failure_mode field. Aggregation code should treat missing failure_mode
as either its own category or default to 'extraction_failure'.
"""

import math
from typing import Any

from secretagent.evaluate import Evaluator


# TODO(Phase 6): tune after observing real react failures.
_STEP_LIMIT_PATTERNS = (
    "usagelimit",
    "usage limit",
    "exceeded the maximum",
    "maximum number of",
    "max_iterations",
)


def _within_tolerance(predicted: Any, expected: Any, tol: float = 0.01) -> bool:
    """True if predicted is within `tol` relative error of expected.

    Near zero (|expected| < 1e-9), falls back to absolute difference < 0.01.
    """
    try:
        p = float(predicted)
        e = float(expected)
    except (TypeError, ValueError):
        return False
    if abs(e) < 1e-9:
        return abs(p - e) < 0.01
    return abs(p - e) / abs(e) <= tol


def _tight_match(predicted: Any, expected: Any) -> bool:
    """True if predicted matches expected at near-IEEE-754 precision."""
    try:
        p = float(predicted)
        e = float(expected)
    except (TypeError, ValueError):
        return False
    return math.isclose(p, e, rel_tol=1e-5, abs_tol=1e-8)


class TaxEvaluator(Evaluator):
    """1%-relative scoring for federal tax predictions.

    Primary metric `correct` is 1% relative tolerance (RuleArena convention).
    `correct_tolerance` is a tight near-exact diagnostic for sensitivity
    analysis. `failure_mode` classifies non-correct predictions into
    actionable categories.
    """

    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        correct = float(_within_tolerance(predicted_output, expected_output, tol=0.01))
        correct_tolerance = float(_tight_match(predicted_output, expected_output))

        if predicted_output is None:
            failure_mode = "calculation_error"
        elif isinstance(predicted_output, str) and predicted_output.startswith("**exception raised**"):
            lower = predicted_output.lower()
            if any(pat in lower for pat in _STEP_LIMIT_PATTERNS):
                failure_mode = "step_limit"
            else:
                failure_mode = "extraction_failure"
        elif correct:
            failure_mode = "none"
        else:
            failure_mode = "calculation_error"

        return dict(
            correct=correct,
            correct_tolerance=correct_tolerance,
            failure_mode=failure_mode,
        )
