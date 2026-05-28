"""Lightweight pytest suite for benchmarks/natural_plan/.

Modeled on tests/test_sports_understanding.py: import a task's ptools +
evaluator, bind the sub-tool interfaces to 'simulate', run the workflow
on a real dataset example, and score it with the task evaluator. One
parametrized case per task (calendar, meeting, trip).

The evaluator test needs no API key — it feeds each task's golden plan
back through its evaluator and checks it scores as correct.
"""

import json
from pathlib import Path

import pytest

from conftest import needs_api_key, CI_TEST_MODEL, load_benchmark_modules
from secretagent import config

NATURAL_PLAN_DIR = Path(__file__).resolve().parent.parent / "natural_plan"

TASKS = {
    "calendar": {
        "workflow": "calendar_workflow",
        "tools": ["parse_schedules", "find_available_slots", "select_and_format"],
        "evaluator": "CalendarEvaluator",
    },
    "meeting": {
        "workflow": "meeting_workflow",
        "tools": ["parse_meeting_info", "plan_visit_order", "build_meeting_plan"],
        "evaluator": "MeetingEvaluator",
    },
    "trip": {
        "workflow": "trip_workflow",
        "tools": ["parse_trip_constraints", "find_valid_route", "build_trip_plan"],
        "evaluator": "TripEvaluator",
    },
}


def _load_task(task):
    """Import the task's ptools and evaluator modules from its subdir."""
    ptools, evaluator_mod = load_benchmark_modules(
        NATURAL_PLAN_DIR / task, "ptools", "evaluator",
    )
    return ptools, evaluator_mod


def _first_case(task):
    """Return (prompt, expected_output) for the first valid.json case."""
    data = json.loads(
        (NATURAL_PLAN_DIR / task / "data" / "valid.json").read_text(encoding="utf-8")
    )
    case = data["cases"][0]
    return case["input_args"][0], case["expected_output"]


def _golden_response(expected_output):
    """Golden plan as a single string (meeting goldens are lists of steps)."""
    golden = expected_output["golden_plan"]
    return " ".join(golden) if isinstance(golden, list) else golden


@pytest.mark.parametrize("task", ["calendar", "meeting", "trip"])
def test_evaluator_scores_golden(task):
    """Each task's evaluator scores its own golden plan as correct."""
    _, evaluator_mod = _load_task(task)
    _, expected_output = _first_case(task)
    evaluator = getattr(evaluator_mod, TASKS[task]["evaluator"])()
    result = evaluator.compare_predictions(_golden_response(expected_output), expected_output)
    assert result["correct"] is True


@needs_api_key
@pytest.mark.parametrize("task", ["calendar", "meeting", "trip"])
def test_workflow(task):
    """Bind sub-tools to 'simulate', run the workflow, and score the result."""
    ptools, evaluator_mod = _load_task(task)
    tc = TASKS[task]
    for tool in tc["tools"]:
        getattr(ptools, tool).implement_via("simulate")

    prompt, expected_output = _first_case(task)
    with config.configuration(llm={"model": CI_TEST_MODEL}):
        result = getattr(ptools, tc["workflow"])(prompt)

    assert isinstance(result, str) and result.strip()
    evaluator = getattr(evaluator_mod, tc["evaluator"])()
    scored = evaluator.compare_predictions(result, expected_output)
    assert isinstance(scored["correct"], bool)
