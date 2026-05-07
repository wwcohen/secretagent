"""Minimal pytest suite for benchmarks/rulearena/.

Test groups:
  TestConfig      — YAML config loads, dotlist overrides, invalid domain raises
  TestCalculators — airline and tax calculators on known inputs (no LLM)
  TestSchema      — Case/Dataset fields, load_dataset returns valid data
  TestMetrics     — _within_tolerance, _isclose_match, compare_predictions
  TestIntegration — L0 (no LLM), L0F, L1 on valid split (4 examples each)
                    L3 excluded: no max_steps cap in pydantic-ai agent, no repo precedent
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from conftest import needs_api_key, CI_TEST_MODEL
from secretagent import config
from secretagent.core import implement_via_config
from secretagent.dataset import Case, Dataset

RULEARENA_DIR = Path(__file__).resolve().parent.parent / "rulearena"
if str(RULEARENA_DIR) not in sys.path:
    sys.path.insert(0, str(RULEARENA_DIR))

DATA_DIR = RULEARENA_DIR / "data"
CONF_FILE = RULEARENA_DIR / "conf" / "conf.yaml"


def _first_record(domain: str) -> dict:
    with open(DATA_DIR / domain / "train.jsonl", encoding="utf-8") as f:
        return json.loads(f.readline())


def _import_rulearena():
    """Import expt and ptools from benchmarks/rulearena/ deterministically.

    Delegates to conftest.load_benchmark_modules so bare-name imports inside
    rulearena/expt.py (which does `import ptools`) resolve to rulearena's
    files even when another benchmark test has polluted sys.path /
    sys.modules in the same pytest process.
    """
    from conftest import load_benchmark_modules
    return load_benchmark_modules(RULEARENA_DIR, "expt", "ptools")


# ===================================================================
# TestConfig — fast, no LLM
# ===================================================================

class TestConfig:
    def setup_method(self):
        config.reset()

    def test_conf_yaml_loads(self):
        """conf.yaml loads and has required top-level keys."""
        config.configure(yaml_file=CONF_FILE)
        assert config.get("llm.model") is not None
        assert config.get("dataset.domain") is not None
        assert config.get("evaluate.result_dir") is not None

    def test_dotlist_override(self):
        """Dotlist overrides replace yaml values."""
        config.configure(yaml_file=CONF_FILE, dotlist=["dataset.domain=nba", "dataset.n=5"])
        assert config.require("dataset.domain") == "nba"
        assert config.require("dataset.n") == 5

    def test_invalid_domain_raises(self):
        """_load_rules raises on unknown domain."""
        expt, _ = _import_rulearena()
        with pytest.raises(ValueError, match="Unknown domain"):
            expt._load_rules("martian_law")


# ===================================================================
# TestCalculators — no LLM, known inputs -> expected outputs
# ===================================================================

class TestCalculators:
    def test_airline_known_output(self):
        """First airline training example: Emily Main Plus London->Minneapolis -> 1275."""
        from calculators.airline import compute_airline_fee
        rec = _first_record("airline")
        assert compute_airline_fee(rec["info"]) == 1275

    def test_tax_known_output(self):
        """First tax training example: John head-of-household -> 4747.5."""
        from calculators.tax import compute_tax_fee
        rec = _first_record("tax")
        result = compute_tax_fee(rec)
        assert result is not None
        assert abs(result - 4747.5) < 0.01

    def test_airline_returns_numeric(self):
        from calculators.airline import compute_airline_fee
        rec = _first_record("airline")
        result = compute_airline_fee(rec["info"])
        assert np.issubdtype(type(result), np.number)

    def test_tax_missing_fields_use_defaults(self):
        """Tax calculator handles partial pydantic dicts via _taxpayer_defaults."""
        from calculators.tax import compute_tax_fee
        rec = _first_record("tax")
        sparse = dict(rec)
        sparse["pydantic"] = {"filing_status": rec["pydantic"]["filing_status"]}
        result = compute_tax_fee(sparse)
        assert result is not None


# ===================================================================
# TestSchema — no LLM, structural checks
# ===================================================================

class TestSchema:
    def setup_method(self):
        config.reset()

    def test_case_has_required_fields(self):
        c = Case(name="test", input_args=("a",), expected_output=42)
        assert c.name == "test"
        assert c.expected_output == 42

    def test_dataset_summary(self):
        cases = [Case(name=f"c{i}", input_args=(i,), expected_output=i) for i in range(3)]
        ds = Dataset(name="test_ds", split="valid", cases=cases)
        assert "size=3" in ds.summary()

    def test_load_dataset_airline(self):
        expt, _ = _import_rulearena()
        config.configure(yaml_file=CONF_FILE)
        ds = expt.load_dataset("airline", "train")
        assert len(ds.cases) > 0
        assert ds.name == "rulearena_airline"
        for case in ds.cases[:3]:
            assert case.name.startswith("airline_")
            assert case.expected_output is not None

    def test_load_dataset_nba(self):
        expt, _ = _import_rulearena()
        config.configure(yaml_file=CONF_FILE)
        ds = expt.load_dataset("nba", "train")
        assert len(ds.cases) > 0
        for case in ds.cases[:3]:
            assert isinstance(case.expected_output, bool)


# ===================================================================
# TestMetrics — no LLM, evaluator logic
# ===================================================================

class TestMetrics:
    def setup_method(self):
        expt, _ = _import_rulearena()
        self._expt = expt
        self.evaluator = expt.RuleArenaEvaluator()

    def test_within_tolerance_exact(self):
        assert self._expt._within_tolerance(100.0, 100.0)

    def test_within_tolerance_close(self):
        assert self._expt._within_tolerance(100.5, 100.0)      # 0.5% < 1%
        assert not self._expt._within_tolerance(102.0, 100.0)   # 2% > 1%

    def test_within_tolerance_zero_expected(self):
        assert self._expt._within_tolerance(0.005, 0.0)         # abs diff < 0.01
        assert not self._expt._within_tolerance(0.05, 0.0)

    def test_isclose_match(self):
        assert self._expt._isclose_match(100.0, 100.0)
        assert self._expt._isclose_match(100.000001, 100.0)
        assert not self._expt._isclose_match(100.5, 100.0)

    def test_compare_predictions_bool(self):
        result = self.evaluator.compare_predictions(True, True)
        assert result["correct"] == 1.0
        assert result["correct_tolerance"] == 1.0
        assert result["failure_mode"] == "none"

        result = self.evaluator.compare_predictions(False, True)
        assert result["correct"] == 0.0
        assert result["failure_mode"] == "calculation_error"

    def test_compare_predictions_numeric(self):
        result = self.evaluator.compare_predictions(100.5, 100.0)
        assert result["correct"] == 1.0           # within 1%
        assert result["correct_tolerance"] == 0.0  # not np.isclose
        assert result["failure_mode"] == "none"

    def test_compare_predictions_non_numeric(self):
        result = self.evaluator.compare_predictions("garbage", 100.0)
        assert result["correct"] == 0.0
        assert result["correct_tolerance"] == 0.0
        assert result["failure_mode"] == "calculation_error"

    def test_compare_predictions_exception_string(self):
        result = self.evaluator.compare_predictions(
            "**exception raised**: ValueError('no answer')", 100.0)
        assert result["failure_mode"] == "extraction_failure"

    def test_compare_predictions_none(self):
        result = self.evaluator.compare_predictions(None, 100.0)
        assert result["failure_mode"] == "extraction_failure"


# ===================================================================
# TestIntegration — real pipeline runs
#   L0:  pure Python oracle, zero LLM calls (no needs_api_key)
#   L0F: chain-of-thought, 1 LLM call per example
#   L1:  LLM extraction + Python calculator
#   L3:  excluded — pydantic-ai agent has no max_steps cap, no repo precedent
# ===================================================================

_L0_DOTLIST = [
    "ptools.compute_rulearena_answer.method=direct",
    "ptools.compute_rulearena_answer.fn=ptools.l0_oracle_workflow",
]

_L0F_DOTLIST = [
    "ptools.compute_rulearena_answer.method=direct",
    "ptools.compute_rulearena_answer.fn=ptools.l0f_cot_workflow",
]

_L1_DOTLIST = [
    "ptools.compute_rulearena_answer.method=direct",
    "ptools.compute_rulearena_answer.fn=ptools.l1_extract_workflow",
]


def _run_eval(domain, extra_dotlist, n=4):
    """Configure pipeline, load n valid-split examples, evaluate, return DataFrame.

    Runs from RULEARENA_DIR so relative paths (prompt templates, data) resolve.
    """
    import pandas as pd
    prev_cwd = os.getcwd()
    try:
        os.chdir(RULEARENA_DIR)
        expt, pt = _import_rulearena()
        # Reset so a prior benchmark's ptools.* keys don't merge into this run.
        config.reset()
        config.configure(
            yaml_file=CONF_FILE,
            dotlist=[f"dataset.domain={domain}"] + extra_dotlist,
        )
        config.set_root(RULEARENA_DIR)
        implement_via_config(pt, config.require("ptools"))
        ds = expt.load_dataset(domain, "valid").configure(n=n)
        evaluator = expt.RuleArenaEvaluator()
        csv_path = evaluator.evaluate(ds, pt.compute_rulearena_answer)
        df = pd.read_csv(csv_path)
        assert len(df) == n
        assert "correct" in df.columns
        return df
    finally:
        os.chdir(prev_cwd)


class TestIntegrationL0:
    """L0 oracle: zero LLM calls, pure Python calculators.
    NBA skipped — no deterministic calculator; ground truth comes from data
    so L0 would trivially return 100% correct, which tests nothing.
    """

    def test_l0_airline(self):
        df = _run_eval("airline", _L0_DOTLIST)
        assert df["correct"].mean() == 1.0  # oracle should be perfect

    def test_l0_tax(self):
        df = _run_eval("tax", _L0_DOTLIST)
        assert df["correct"].mean() == 1.0


@needs_api_key
class TestIntegrationL0F:
    """L0F chain-of-thought: 1 LLM call per example."""

    def test_l0f_airline(self):
        df = _run_eval("airline", [f"llm.model={CI_TEST_MODEL}"] + _L0F_DOTLIST)
        assert "correct" in df.columns

    def test_l0f_nba(self):
        df = _run_eval("nba", [f"llm.model={CI_TEST_MODEL}"] + _L0F_DOTLIST)
        assert "correct" in df.columns

    def test_l0f_tax(self):
        df = _run_eval("tax", [f"llm.model={CI_TEST_MODEL}"] + _L0F_DOTLIST)
        assert "correct" in df.columns


@needs_api_key
class TestIntegrationL1:
    """L1 extraction: LLM extracts structured params, Python computes answer."""

    def test_l1_airline(self):
        df = _run_eval("airline", [f"llm.model={CI_TEST_MODEL}"] + _L1_DOTLIST)
        assert "correct" in df.columns

    def test_l1_nba(self):
        df = _run_eval("nba", [f"llm.model={CI_TEST_MODEL}"] + _L1_DOTLIST)
        assert "correct" in df.columns

    def test_l1_tax(self):
        df = _run_eval("tax", [f"llm.model={CI_TEST_MODEL}"] + _L1_DOTLIST)
        assert "correct" in df.columns
