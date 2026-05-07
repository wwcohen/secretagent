"""AirlineEvaluator: exact-match scoring with tolerance diagnostic.

Produces three metrics per case:
  correct            - 1.0 if |pred - exp| <= 1e-6 (exact match + IEEE-754 noise slack)
  correct_tolerance  - 1.0 if |pred - exp| / |exp| <= 0.01 (1% relative, diagnostic)
  failure_mode       - "none" | "calculation_error" | "extraction_failure" | "step_limit"

The primary metric (correct) is exact match because that's what RuleArena's
paper reports and what reviewers will expect when comparing to the benchmark.
The abs_tol=1e-6 is IEEE-754 floating-point-accumulation insurance, not
reviewer-visible slack. correct_tolerance is a diagnostic for sensitivity
analysis.

failure_mode distinguishes react's step-limit exhaustion from generic
pipeline exceptions, since the former is a characteristic failure mode
of tool-using agents and worth reporting separately in the paper.

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
# Heuristic patterns for pydantic-ai step-limit exhaustion. Substring
# match on the stringified exception (case-insensitive). The current
# list covers common messages from UsageLimitExceeded and related
# exception types.
_STEP_LIMIT_PATTERNS = (
    "usagelimit",
    "usage limit",
    "exceeded the maximum",
    "maximum number of",
    "max_iterations",
)


def _exact_match(predicted: Any, expected: Any) -> bool:
    """True if predicted matches expected within IEEE-754 noise (abs_tol=1e-6).

    Integer and exactly-representable-float comparisons already succeed as
    equal in Python; the 1e-6 tolerance only absorbs floating-point
    accumulation error from upstream arithmetic.
    """
    try:
        p = float(predicted)
        e = float(expected)
    except (TypeError, ValueError):
        return False
    return math.isclose(p, e, rel_tol=0, abs_tol=1e-6)


def _within_tolerance(predicted: Any, expected: Any, tol: float = 0.01) -> bool:
    """True if predicted is within `tol` relative error of expected.

    Near zero (|expected| < 1e-9), falls back to absolute difference < 0.01.
    Diagnostic metric - not the primary score.
    """
    try:
        p = float(predicted)
        e = float(expected)
    except (TypeError, ValueError):
        return False
    if abs(e) < 1e-9:
        return abs(p - e) < 0.01
    return abs(p - e) / abs(e) <= tol


class AirlineEvaluator(Evaluator):
    """Exact-match scoring for airline baggage fee predictions.

    Primary metric `correct` is exact match (up to IEEE-754 noise).
    `correct_tolerance` (1% relative) is a diagnostic for sensitivity
    analysis. `failure_mode` classifies non-correct predictions into
    actionable categories.
    """

    def compare_predictions(self, predicted_output, expected_output) -> dict[str, Any]:
        correct = float(_exact_match(predicted_output, expected_output))
        correct_tolerance = float(_within_tolerance(predicted_output, expected_output))

        if predicted_output is None:
            # Strategy context isn't available here. For unstructured_baseline,
            # None would mean parse_numeric_answer couldn't extract (genuine
            # extraction failure); for workflow/pot/react, None means the
            # pipeline completed but produced no usable numeric value (a
            # calculation outcome). Defaulting to calculation_error is safer
            # than over-claiming extraction failure across strategies.
            # TODO: thread strategy into the evaluator (or post-process from
            # config) to split unstructured None -> extraction_failure.
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
