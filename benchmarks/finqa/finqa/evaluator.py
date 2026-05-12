"""FinQA scoring: numeric-tolerant match; unlabeled splits skip ``correct``."""

from __future__ import annotations

import math
import re
from typing import Any

from secretagent.evaluate import Evaluator


def normalize_finqa_prediction(raw: Any) -> str:
    """Strip common scaffolding; prefer content inside ``<answer>...</answer>``.

    When the prediction is multi-line, prefer the *first* line that looks
    like a number over blindly taking the last line (which is often an
    explanation).
    """
    s = str(raw).strip().strip('"').strip("'")
    m = re.search(r"<answer[^>]*>(.*?)</answer>", s, flags=re.DOTALL | re.IGNORECASE)
    if m:
        s = m.group(1).strip()
    else:
        s = re.sub(r"</?answer[^>]*>", "", s, flags=re.IGNORECASE).strip()
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    if not lines:
        return s.strip()
    # Prefer the first line that parses as a number (possibly with $, %, commas)
    _NUM_RE = re.compile(
        r'^[$€£]?\s*-?\s*[\d,]+\.?\d*\s*%?$'
    )
    for ln in lines:
        if _NUM_RE.match(ln.strip().rstrip('.')):
            return ln.strip().rstrip('.')
    return lines[-1]


def _strip_answer(s: str) -> str:
    s = s.strip().strip('"').strip("'")
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    if lines:
        s = lines[-1]
    return s.strip()


def _to_float_token(s: str) -> float | None:
    t = s.lower().replace(",", "")
    t = re.sub(r"[$€£]", "", t)
    t = t.strip().rstrip("%").strip()
    # Strip trailing units that models commonly append
    t = re.sub(r"\s*(million|billion|thousand|m|b|k)s?\s*$", "", t, flags=re.IGNORECASE).strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _numeric_match_float(
    pred_s: str, raw_predicted: str, expected: float
) -> bool:
    """Match parsed number; FinQA gold often stores rates as decimals (0.935) vs ``93.5%``."""
    pf = _to_float_token(pred_s)
    if pf is None:
        return False
    pred_has_percent = "%" in raw_predicted or "%" in pred_s

    # FinQA gold keeps many decimal places; model output is often rounded.
    # rel_tol=2e-3 accepts e.g. 4.85 ≈ 4.85514, 24.7% ≈ 24.69136.
    if math.isclose(pf, expected, rel_tol=2e-3, abs_tol=1e-3):
        return True
    if pred_has_percent and math.isclose(
        pf / 100.0, expected, rel_tol=2e-3, abs_tol=1e-5
    ):
        return True
    return False


def finqa_answers_match(predicted: Any, expected: Any) -> bool:
    """Return True if prediction matches gold (numeric tolerance or string)."""
    if expected is None:
        return False

    raw = str(predicted)
    pred_s = normalize_finqa_prediction(raw)

    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return _numeric_match_float(pred_s, raw, float(expected))

    exp_s = _strip_answer(str(expected))
    ef = _to_float_token(exp_s)
    pf = _to_float_token(pred_s)
    if ef is not None and pf is not None:
        if math.isclose(pf, ef, rel_tol=1e-4, abs_tol=1e-4):
            return True
        if "%" in raw or "%" in pred_s:
            if math.isclose(pf / 100.0, ef, rel_tol=1e-3, abs_tol=1e-5):
                return True

    return pred_s.lower() == exp_s.lower()


class FinQAEvaluator(Evaluator):
    """Compare model output to FinQA gold; ``expected_output`` None → no score."""

    def compare_predictions(self, predicted_output: Any, expected_output: Any) -> dict[str, Any]:
        if expected_output is None:
            return {"correct": float("nan"), "scored": False}
        ok = finqa_answers_match(predicted_output, expected_output)
        return {"correct": 1.0 if ok else 0.0, "scored": True}
