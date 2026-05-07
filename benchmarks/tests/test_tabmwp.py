"""Lightweight pytest suite for benchmarks/tabmwp/.

Runs all 5 standard experiments on 4 examples each to catch regressions.
Uses dev1k split (not test1k).

Test groups:
  TestBasics — unstructured_baseline, structured_baseline, workflow, pot, react
               (4 examples each, dev1k split, CI_TEST_MODEL)
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

from conftest import needs_api_key, CI_TEST_MODEL
from secretagent import config
from secretagent.core import implement_via_config

TABMWP_DIR = Path(__file__).resolve().parent.parent / "tabmwp"
if str(TABMWP_DIR) not in sys.path:
    sys.path.insert(0, str(TABMWP_DIR))


def _import_ptools():
    """Import ptools from benchmarks/tabmwp/ deterministically."""
    from conftest import load_benchmark_modules
    (ptools,) = load_benchmark_modules(TABMWP_DIR, "ptools")
    return ptools


def _run_eval(tmp_path, conf_file, extra_dotlist=None, n=4):
    """Load config, set up table store, run n examples, return DataFrame."""
    import json
    from conftest import load_benchmark_modules
    from secretagent.dataset import Dataset, Case

    prev_cwd = os.getcwd()
    try:
        os.chdir(TABMWP_DIR)

        # Load ptools and expt together so the second call does not purge
        # the first: load_benchmark_modules clears colliding sys.modules
        # entries, so grabbing them in one call keeps both references live.
        ptools, expt_mod = load_benchmark_modules(TABMWP_DIR, "ptools", "expt")
        TabMWPEvaluator = expt_mod.TabMWPEvaluator

        # Reset so a prior benchmark's ptools.* keys don't merge into this run.
        config.reset()
        config.configure(
            yaml_file=TABMWP_DIR / "conf" / conf_file,
            dotlist=[
                f"llm.model={CI_TEST_MODEL}",
                f"evaluate.result_dir={tmp_path}",
                f"dataset.n={n}",
                "dataset.split=dev1k",
                "cachier.enable_caching=False",
            ] + (extra_dotlist or []),
        )
        config.set_root(TABMWP_DIR)

        split = config.get("dataset.split", "dev1k")
        raw_data = json.loads((TABMWP_DIR / "data" / f"problems_{split}.json").read_text())
        ptools.load_table_store(raw_data)

        implement_via_config(ptools, config.require("ptools"))

        # Build dataset from raw data using same logic as expt.py
        cases = []
        for ex_id, ex in list(raw_data.items())[:n]:
            cases.append(Case(
                name=ex_id,
                input_args=(ex["question"], ex["table"], ex_id, ex["choices"]),
                expected_output=str(ex["answer"]),
                metadata={
                    "ques_type": ex.get("ques_type"),
                    "ans_type": ex.get("ans_type"),
                    "grade": ex.get("grade"),
                },
            ))
        dataset = Dataset(name="tabmwp", split=split, cases=cases)
        dataset.configure(shuffle_seed=42, n=n)

        entry_point = config.get("evaluate.entry_point", "tabmwp_solve")
        interface = getattr(ptools, entry_point)

        evaluator = TabMWPEvaluator()
        csv_path = evaluator.evaluate(dataset, interface)
        df = pd.read_csv(csv_path)
        assert len(df) == n
        assert "correct" in df.columns
        return df
    finally:
        os.chdir(prev_cwd)


@needs_api_key
class TestBasics:
    """Integration tests for all 5 standard TabMWP experiments, 4 examples each."""

    def test_unstructured_baseline(self, tmp_path):
        df = _run_eval(tmp_path, "unstructured_baseline.yaml")
        assert "correct" in df.columns

    def test_structured_baseline(self, tmp_path):
        df = _run_eval(tmp_path, "structured_baseline.yaml")
        assert "correct" in df.columns

    def test_workflow(self, tmp_path):
        df = _run_eval(tmp_path, "workflow.yaml")
        assert "correct" in df.columns

    def test_pot(self, tmp_path):
        df = _run_eval(tmp_path, "pot.yaml")
        assert "correct" in df.columns

    def test_react(self, tmp_path):
        df = _run_eval(tmp_path, "react.yaml",
                       extra_dotlist=["evaluate.entry_point=tabmwp_react"])
        assert "correct" in df.columns
