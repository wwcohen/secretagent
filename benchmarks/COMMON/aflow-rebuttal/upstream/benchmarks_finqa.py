# -*- coding: utf-8 -*-
# @Desc    : FinQA benchmark. Scoring ported verbatim from the secretagent
#            harness (benchmarks/finqa/evaluator.py) so the AFlow arm and the
#            reference cells use identical answer matching.
from __future__ import annotations

import math
import re
from typing import Any, Callable, List, Tuple

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from benchmarks.benchmark import BaseBenchmark
from scripts.logs import logger


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
    _NUM_RE = re.compile(r'^[$€£]?\s*-?\s*[\d,]+\.?\d*\s*%?$')
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


def _to_float_token(s: str):
    t = s.lower().replace(",", "")
    t = re.sub(r"[$€£]", "", t)
    t = t.strip().rstrip("%").strip()
    t = re.sub(r"\s*(million|billion|thousand|m|b|k)s?\s*$", "", t, flags=re.IGNORECASE).strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _numeric_match_float(pred_s: str, raw_predicted: str, expected: float) -> bool:
    """Match parsed number; FinQA gold often stores rates as decimals (0.935) vs ``93.5%``."""
    pf = _to_float_token(pred_s)
    if pf is None:
        return False
    pred_has_percent = "%" in raw_predicted or "%" in pred_s

    if math.isclose(pf, expected, rel_tol=2e-3, abs_tol=1e-3):
        return True
    if pred_has_percent and math.isclose(pf / 100.0, expected, rel_tol=2e-3, abs_tol=1e-5):
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


class FinQABenchmark(BaseBenchmark):
    def __init__(self, name: str, file_path: str, log_path: str):
        super().__init__(name, file_path, log_path)

    def calculate_score(self, expected_output: Any, prediction: str) -> Tuple[float, str]:
        ok = finqa_answers_match(prediction, expected_output)
        return (1.0 if ok else 0.0), normalize_finqa_prediction(str(prediction))

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1), retry=retry_if_exception_type(Exception), reraise=True)
    async def _generate_output(self, graph, input_text):
        return await graph(input_text)

    async def evaluate_problem(self, problem: dict, graph: Callable) -> Tuple[str, str, Any, float, float]:
        input_text = problem["question"]
        expected_output = problem["answer"]

        try:
            output, cost = await self._generate_output(graph, input_text)
            score, extracted_output = self.calculate_score(expected_output, output)

            if score == 0:
                self.log_mismatch(input_text, expected_output, output, extracted_output)

            return input_text, output, expected_output, score, cost

        except Exception as e:
            logger.info(f"Maximum retries reached. Skipping this sample. Error: {e}")
            return input_text, str(e), expected_output, 0.0, 0.0

    def get_result_columns(self) -> List[str]:
        return ["question", "prediction", "expected_output", "score", "cost"]
