"""Lightweight pytest suite for benchmarks/natural_plan/.

Mirrors the Makefile baselines (unstructured, structured, workflow, pot, react)
across all three tasks (calendar, meeting, trip) — 15 tests total, 2 examples each.
"""

import importlib
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

from conftest import needs_api_key, CI_TEST_MODEL
from secretagent import config
from secretagent.core import implement_via_config

NATURAL_PLAN_DIR = Path(__file__).resolve().parent.parent / "natural_plan"

TASK_CONFIG = {
    "calendar": {
        "config_file": "conf/calendar.yaml",
        "ptools_module": "ptools_calendar",
        "interface": "calendar_scheduling",
        "workflow_fn": "ptools_calendar.calendar_workflow",
        "tools": ["parse_schedules", "find_available_slots", "select_and_format"],
    },
    "meeting": {
        "config_file": "conf/meeting.yaml",
        "ptools_module": "ptools_meeting",
        "interface": "meeting_planning",
        "workflow_fn": "ptools_meeting.meeting_workflow",
        "tools": ["parse_meeting_info", "plan_visit_order", "build_meeting_plan"],
    },
    "trip": {
        "config_file": "conf/trip.yaml",
        "ptools_module": "ptools_trip",
        "interface": "trip_planning",
        "workflow_fn": "ptools_trip.trip_workflow",
        "tools": ["parse_trip_constraints", "find_valid_route", "build_trip_plan"],
    },
}


def _import_modules(task):
    """Import ptools, eval_utils, and expt from benchmarks/natural_plan/."""
    from conftest import load_benchmark_modules
    tc = TASK_CONFIG[task]
    ptools_mod, _eval_utils, expt_mod = load_benchmark_modules(
        NATURAL_PLAN_DIR, tc["ptools_module"], "eval_utils", "expt",
    )
    return ptools_mod, expt_mod.NaturalPlanEvaluator, expt_mod.load_dataset


def _run_eval(tmp_path, task, extra_dotlist, n=2):
    """Configure pipeline, load n examples, evaluate, return DataFrame."""
    prev_cwd = os.getcwd()
    try:
        os.chdir(NATURAL_PLAN_DIR)
        ptools_mod, NaturalPlanEvaluator, load_dataset = _import_modules(task)
        tc = TASK_CONFIG[task]

        # Reset global config to avoid cross-task contamination
        config.reset()

        conf_path = NATURAL_PLAN_DIR / tc["config_file"]
        config.configure(
            yaml_file=str(conf_path),
            dotlist=[
                f"llm.model={CI_TEST_MODEL}",
                f"evaluate.result_dir={tmp_path}",
                f"dataset.n={n}",
                "dataset.prompt_mode=0shot",
            ] + extra_dotlist,
        )
        config.set_root(NATURAL_PLAN_DIR)
        implement_via_config(ptools_mod, config.require("ptools"))

        dataset = load_dataset(task, prompt_mode="0shot")
        dataset.configure(
            shuffle_seed=config.get("dataset.shuffle_seed"),
            n=n,
        )

        interface = getattr(ptools_mod, tc["interface"])
        evaluator = NaturalPlanEvaluator(task)
        csv_path = evaluator.evaluate(dataset, interface)
        df = pd.read_csv(csv_path)
        assert len(df) == n
        assert "correct" in df.columns
        return df
    finally:
        os.chdir(prev_cwd)


def _structured_dotlist(task):
    iface = TASK_CONFIG[task]["interface"]
    return [
        f"evaluate.expt_name=test_{task}_structured",
        f"ptools.{iface}.method=simulate",
    ]


def _unstructured_dotlist(task):
    iface = TASK_CONFIG[task]["interface"]
    return [
        f"evaluate.expt_name=test_{task}_unstructured",
        f"ptools.{iface}.method=prompt_llm",
        f"ptools.{iface}.prompt_template_file=prompt_templates/zeroshot_{task}.txt",
    ]


def _workflow_dotlist(task):
    tc = TASK_CONFIG[task]
    return [
        f"evaluate.expt_name=test_{task}_workflow",
        f"ptools.{tc['interface']}.method=direct",
        f"ptools.{tc['interface']}.fn={tc['workflow_fn']}",
    ]


def _pot_dotlist(task):
    tc = TASK_CONFIG[task]
    mod = tc["ptools_module"]
    tools = ",".join(f"{mod}.{t}" for t in tc["tools"])
    return [
        f"evaluate.expt_name=test_{task}_pot",
        f"ptools.{tc['interface']}.method=program_of_thought",
        f"ptools.{tc['interface']}.tools=[{tools}]",
    ]


def _react_dotlist(task):
    tc = TASK_CONFIG[task]
    mod = tc["ptools_module"]
    tools = ",".join(f"{mod}.{t}" for t in tc["tools"])
    return [
        f"evaluate.expt_name=test_{task}_react",
        f"ptools.{tc['interface']}.method=simulate_pydantic",
        f"ptools.{tc['interface']}.tools=[{tools}]",
    ]


@needs_api_key
class TestNaturalPlanBasics:
    """Integration tests matching the Makefile baselines, 2 examples each."""

    @pytest.mark.parametrize("task", ["calendar", "meeting", "trip"])
    def test_structured_baseline(self, tmp_path, task):
        df = _run_eval(tmp_path, task, _structured_dotlist(task))
        assert "correct" in df.columns

    @pytest.mark.parametrize("task", ["calendar", "meeting", "trip"])
    def test_unstructured_baseline(self, tmp_path, task):
        df = _run_eval(tmp_path, task, _unstructured_dotlist(task))
        assert "correct" in df.columns

    @pytest.mark.parametrize("task", ["calendar", "meeting", "trip"])
    def test_workflow(self, tmp_path, task):
        df = _run_eval(tmp_path, task, _workflow_dotlist(task))
        assert "correct" in df.columns

    @pytest.mark.parametrize("task", ["calendar", "meeting", "trip"])
    def test_pot(self, tmp_path, task):
        df = _run_eval(tmp_path, task, _pot_dotlist(task))
        assert "correct" in df.columns

    @pytest.mark.parametrize("task", ["calendar", "meeting", "trip"])
    def test_react(self, tmp_path, task):
        df = _run_eval(tmp_path, task, _react_dotlist(task))
        assert "correct" in df.columns
