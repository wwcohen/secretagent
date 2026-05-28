"""No-arg evaluator for the NaturalPlan calendar-scheduling task.

Used by the generic runner, e.g.::

    uv run python -m secretagent.cli.expt run --config conf/calendar.yaml \
      --evaluator evaluator.CalendarEvaluator

Trace info (full rollouts) is captured by setting
``evaluate.record_details=true``; the base Evaluator writes it into
results.jsonl.

Eval logic adapted from natural-plan/evaluate_calendar.py
(Google DeepMind, Apache 2.0 License).
"""
import re
from typing import Tuple

from secretagent.evaluate import Evaluator


def calendar_hour_to_num(hr_str: str) -> float:
    """Convert 'HH:MM' to numeric hours (e.g., '14:30' -> 14.5)."""
    parts = hr_str.split(':')
    return float(parts[0]) + (0.5 if parts[1] == '30' else 0.0)


def calendar_parse_response(response: str) -> Tuple[str, float, float]:
    """Parse calendar scheduling response.

    Returns (day, start_hour, end_hour).
    Expected format: 'Monday, 14:30 - 15:30'
    """
    time_strs = re.findall(r'[A-Za-z]+, [0-9]+:[0-9]+ - [0-9]+:[0-9]+', response)
    if not time_strs:
        return '', -1, -1
    time_str = time_strs[0]
    day, hour_str = time_str.split(',')[0].strip(), time_str.split(',')[1].strip()
    start_hour, end_hour = hour_str.split('-')[0].strip(), hour_str.split('-')[1].strip()
    return day, calendar_hour_to_num(start_hour), calendar_hour_to_num(end_hour)


def eval_calendar_single(response: str, golden: str) -> bool:
    """Evaluate a single calendar scheduling instance. Returns True if correct."""
    r_day, r_start, r_end = calendar_parse_response(response)
    s_day, s_start, s_end = calendar_parse_response(golden)
    return r_day == s_day and r_start == s_start and r_end == s_end


class CalendarEvaluator(Evaluator):
    def compare_predictions(self, predicted_output, expected_output):
        pred = str(predicted_output) if predicted_output is not None else ''
        return dict(correct=eval_calendar_single(pred, expected_output['golden_plan']))
