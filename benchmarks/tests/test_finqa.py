"""Pytest suite for benchmarks/finqa/.

Test groups:
  TestConfig    — conf.yaml loads with required keys (no LLM)
  TestSchema    — valid.json parses, cases have expected fields (no LLM)
  TestEvaluator — FinQAEvaluator scoring logic on known pairs (no LLM)
  TestBasics    — integration tests matching Makefile targets, 4 examples each:
                  structured_baseline, unstructured_baseline, pot, react, workflow
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from omegaconf import OmegaConf

from conftest import needs_api_key, CI_TEST_MODEL
from secretagent import config
from secretagent.core import implement_via_config
from secretagent.dataset import Case, Dataset

FINQA_DIR = Path(__file__).resolve().parent.parent / "finqa"
CONF_FILE = FINQA_DIR / "conf" / "conf.yaml"

if str(FINQA_DIR) not in sys.path:
    sys.path.insert(0, str(FINQA_DIR))


def _import_finqa():
    """Import ptools and evaluator from benchmarks/finqa/ deterministically."""
    from conftest import load_benchmark_modules
    return load_benchmark_modules(FINQA_DIR, "ptools", "evaluator")


def _run_eval(tmp_path, extra_dotlist, n=4):
    """Configure pipeline, load n valid-split examples, evaluate, return DataFrame.

    Results are written to tmp_path so benchmark results/ stays clean.
    """
    prev_cwd = os.getcwd()
    try:
        os.chdir(FINQA_DIR)
        ptools, evaluator_mod = _import_finqa()
        config.configure(
            yaml_file=CONF_FILE,
            dotlist=[
                f"llm.model={CI_TEST_MODEL}",
                f"evaluate.result_dir={tmp_path}",
            ] + extra_dotlist,
        )
        config.set_root(FINQA_DIR)
        implement_via_config(ptools, config.require("ptools"))

        dataset_file = FINQA_DIR / "data" / "valid.json"
        dataset = Dataset.model_validate_json(dataset_file.read_text())
        dataset.configure(n=n)

        ev = evaluator_mod.FinQAEvaluator()
        csv_path = ev.evaluate(dataset, ptools.answer_finqa)
        df = pd.read_csv(csv_path)
        assert len(df) == n
        assert "correct" in df.columns
        return df
    finally:
        os.chdir(prev_cwd)


# ===================================================================
# TestConfig — fast, no LLM
# ===================================================================

class TestConfig:
    def setup_method(self):
        config.GLOBAL_CONFIG = OmegaConf.create()

    def test_conf_yaml_loads(self):
        """conf.yaml loads and has required top-level keys."""
        config.configure(yaml_file=CONF_FILE)
        assert config.get("llm.model") is not None
        assert config.get("dataset.split") is not None
        assert config.get("evaluate.result_dir") is not None
        assert config.get("ptools.answer_finqa.method") is not None

    def test_dotlist_override(self):
        """Dotlist overrides replace yaml values."""
        config.configure(yaml_file=CONF_FILE, dotlist=["dataset.n=10", "dataset.split=test"])
        assert config.require("dataset.n") == 10
        assert config.require("dataset.split") == "test"


# ===================================================================
# TestSchema — no LLM, structural checks
# ===================================================================

class TestSchema:
    def test_valid_json_parses(self):
        """valid.json deserializes into a Dataset with cases."""
        dataset_file = FINQA_DIR / "data" / "valid.json"
        if not dataset_file.exists():
            pytest.skip("valid.json not built; run make build first")
        ds = Dataset.model_validate_json(dataset_file.read_text())
        assert len(ds.cases) > 0
        assert ds.split == "valid"

    def test_case_has_expected_fields(self):
        dataset_file = FINQA_DIR / "data" / "valid.json"
        if not dataset_file.exists():
            pytest.skip("valid.json not built")
        ds = Dataset.model_validate_json(dataset_file.read_text())
        case = ds.cases[0]
        assert case.name.startswith("valid.")
        assert isinstance(case.input_args, list)
        assert len(case.input_args) == 1
        assert isinstance(case.input_args[0], str)
        assert case.metadata is not None
        assert "finqa_id" in case.metadata

    def test_case_expected_output_is_numeric(self):
        dataset_file = FINQA_DIR / "data" / "valid.json"
        if not dataset_file.exists():
            pytest.skip("valid.json not built")
        ds = Dataset.model_validate_json(dataset_file.read_text())
        for case in ds.cases[:10]:
            assert case.expected_output is not None
            assert isinstance(case.expected_output, (int, float, str))


# ===================================================================
# TestEvaluator — no LLM, evaluator logic on known pairs
# ===================================================================

class TestEvaluator:
    def setup_method(self):
        _, evaluator_mod = _import_finqa()
        self.ev = evaluator_mod.FinQAEvaluator()
        self.match = evaluator_mod.finqa_answers_match

    def test_exact_numeric(self):
        assert self.match("127.4", 127.4)

    def test_dollar_sign(self):
        assert self.match("$127.40", 127.4)

    def test_percent_vs_decimal(self):
        assert self.match("93.5%", 0.935)

    def test_close_rounding(self):
        assert self.match("24.7%", 24.69136)

    def test_wrong_answer(self):
        assert not self.match("18.6", 19.2)

    def test_answer_tag_extraction(self):
        assert self.match("tags.\n<answer>\n24.69%</answer>", 24.69136)

    def test_none_expected(self):
        assert not self.match("42", None)

    def test_string_match(self):
        assert self.match("yes", "yes")
        assert not self.match("yes", "no")

    def test_compare_predictions_correct(self):
        result = self.ev.compare_predictions("127.4", 127.4)
        assert result["correct"] == 1.0
        assert result["scored"] is True

    def test_compare_predictions_wrong(self):
        result = self.ev.compare_predictions("999", 127.4)
        assert result["correct"] == 0.0

    def test_compare_predictions_none_expected(self):
        import math
        result = self.ev.compare_predictions("42", None)
        assert math.isnan(result["correct"])
        assert result["scored"] is False

    def test_exception_string(self):
        result = self.ev.compare_predictions(
            "**exception raised**: ValueError('no answer')", 127.4)
        assert result["correct"] == 0.0



# ===================================================================
# TestBasics — integration tests matching Makefile targets, 4 examples
# ===================================================================

# Dotlist overrides mirror the Makefile commands

_STRUCTURED_BASELINE = [
    "evaluate.expt_name=test_structured_baseline",
    "ptools.answer_finqa.method=simulate",
]

_UNSTRUCTURED_BASELINE = [
    "evaluate.expt_name=test_unstructured_baseline",
    "ptools.answer_finqa.method=direct",
    "ptools.answer_finqa.fn=ptools.unstructured_baseline_workflow",
]

_POT = [
    "evaluate.expt_name=test_pot",
    "ptools.parse_table.method=direct",
    "ptools.compute.method=direct",
    "ptools.answer_finqa.method=program_of_thought",
    "ptools.answer_finqa.tools=[ptools.parse_table,ptools.compute]",
    "ptools.answer_finqa.inject_args=true",
    "ptools.answer_finqa.additional_imports=[re]",
]

_REACT = [
    "evaluate.expt_name=test_react",
    "ptools.parse_table.method=direct",
    "ptools.lookup_cell.method=direct",
    "ptools.compute.method=direct",
    "ptools.extract_reasoning_plan.method=simulate",
    "ptools.extract_final_number.method=simulate",
    "ptools.answer_finqa.method=simulate_pydantic",
    "ptools.answer_finqa.tools=[ptools.call_parse_table,ptools.call_lookup_cell,ptools.call_compute,ptools.call_extract_reasoning_plan]",
]

_WORKFLOW = [
    "evaluate.expt_name=test_workflow",
    "ptools.parse_table.method=direct",
    "ptools.compute.method=direct",
    "ptools.extract_reasoning_plan.method=simulate",
    "ptools.extract_final_number.method=simulate",
    "ptools.answer_finqa.method=direct",
    "ptools.answer_finqa.fn=ptools.answer_finqa_workflow",
]


@needs_api_key
class TestBasics:
    """Integration tests matching the Makefile targets, 4 examples each."""

    def test_structured_baseline(self, tmp_path):
        df = _run_eval(tmp_path, _STRUCTURED_BASELINE)
        assert "correct" in df.columns

    def test_unstructured_baseline(self, tmp_path):
        df = _run_eval(tmp_path, _UNSTRUCTURED_BASELINE)
        assert "correct" in df.columns

    def test_pot(self, tmp_path):
        df = _run_eval(tmp_path, _POT)
        assert "correct" in df.columns

    def test_react(self, tmp_path):
        df = _run_eval(tmp_path, _REACT)
        assert "correct" in df.columns

    def test_workflow(self, tmp_path):
        df = _run_eval(tmp_path, _WORKFLOW)
        assert "correct" in df.columns
