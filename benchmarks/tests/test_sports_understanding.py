"""Lightweight pytest suite for benchmarks/bbh/sports_understanding/.

Mirrors the Makefile 'basics' target (unstructured_baseline, structured_baseline,
workflow, pot, react) but runs only 4 examples each.
"""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from conftest import needs_api_key, CI_TEST_MODEL
from secretagent import config
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset
from secretagent.evaluate import ExactMatchEvaluator

SPORTS_DIR = Path(__file__).resolve().parent.parent / "bbh" / "sports_understanding"
CONF_FILE = SPORTS_DIR / "conf" / "conf.yaml"


def _import_ptools():
    """Import ptools from benchmarks/bbh/sports_understanding/ deterministically."""
    from conftest import load_benchmark_modules
    (ptools,) = load_benchmark_modules(SPORTS_DIR, "ptools")
    return ptools


def _run_eval(tmp_path, extra_dotlist, n=4):
    """Configure pipeline, load n valid-split examples, evaluate, return DataFrame.

    Results are written to tmp_path so benchmark results/ stays clean.
    """
    prev_cwd = os.getcwd()
    try:
        os.chdir(SPORTS_DIR)
        ptools = _import_ptools()
        # Reset so a prior benchmark's ptools.* keys don't merge into this run.
        config.reset()
        config.configure(
            yaml_file=CONF_FILE,
            dotlist=[
                f"llm.model={CI_TEST_MODEL}",
                f"evaluate.result_dir={tmp_path}",
            ] + extra_dotlist,
        )
        config.set_root(SPORTS_DIR)
        implement_via_config(ptools, config.require("ptools"))

        dataset_file = SPORTS_DIR / "data" / "valid.json"
        dataset = Dataset.model_validate_json(dataset_file.read_text())
        dataset.configure(
            shuffle_seed=config.get("dataset.shuffle_seed"),
            n=n,
        )

        evaluator = ExactMatchEvaluator()
        csv_path = evaluator.evaluate(dataset, ptools.are_sports_in_sentence_consistent)
        df = pd.read_csv(csv_path)
        assert len(df) == n
        assert "correct" in df.columns
        return df
    finally:
        os.chdir(prev_cwd)


# Dotlist overrides matching each Makefile target

_UNSTRUCTURED_BASELINE = [
    "evaluate.expt_name=test_unstructured_baseline",
    "ptools.are_sports_in_sentence_consistent.method=direct",
    "ptools.are_sports_in_sentence_consistent.fn=ptools.zeroshot_unstructured_workflow",
]

_STRUCTURED_BASELINE = [
    "evaluate.expt_name=test_structured_baseline",
    "ptools.are_sports_in_sentence_consistent.method=simulate",
]

_WORKFLOW = [
    "evaluate.expt_name=test_workflow",
    "ptools.are_sports_in_sentence_consistent.method=direct",
    "ptools.are_sports_in_sentence_consistent.fn=ptools.sports_understanding_workflow",
]

_POT = [
    "evaluate.expt_name=test_pot",
    "ptools.are_sports_in_sentence_consistent.method=program_of_thought",
    "ptools.are_sports_in_sentence_consistent.tools=[ptools.analyze_sentence,ptools.sport_for,ptools.consistent_sports]",
]

_REACT = [
    "evaluate.expt_name=test_react",
    "ptools.are_sports_in_sentence_consistent.method=simulate_pydantic",
    "ptools.are_sports_in_sentence_consistent.tools=[ptools.analyze_sentence,ptools.sport_for,ptools.consistent_sports]",
]


@needs_api_key
class TestBasics:
    """Integration tests matching the Makefile 'basics' target, 4 examples each."""

    def test_unstructured_baseline(self, tmp_path):
        df = _run_eval(tmp_path, _UNSTRUCTURED_BASELINE)
        assert "correct" in df.columns

    def test_structured_baseline(self, tmp_path):
        df = _run_eval(tmp_path, _STRUCTURED_BASELINE)
        assert "correct" in df.columns

    def test_workflow(self, tmp_path):
        df = _run_eval(tmp_path, _WORKFLOW)
        assert "correct" in df.columns

    def test_pot(self, tmp_path):
        df = _run_eval(tmp_path, _POT)
        assert "correct" in df.columns

    def test_react(self, tmp_path):
        df = _run_eval(tmp_path, _REACT)
        assert "correct" in df.columns
