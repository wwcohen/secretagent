"""Pytest suite for benchmarks/medcalc/ (MedCalc-Bench).

Covers the benchmark's own expt.py + accuracy.py:
  TestExtractNumber — _extract_number parses LLM outputs to floats (no LLM)
  TestAccuracy      — calculate_accuracy tolerance/exact/limits rules (no LLM)
  TestSampling      — stratified / per-calculator samplers (no LLM, synthetic)
  TestDataset       — load_dataset parses the offline snapshot into Cases
                      (skipped when the gitignored data/ snapshot is absent,
                      so it never triggers a live HuggingFace download in CI)
  TestIntegration   — simulate strategy on a few cases (needs an API key;
                      results go to tmp_path, not the benchmark results/)

medcalc keeps its own expt.py (typer app) rather than the shared
run_experiment driver, like natural_plan/rulearena, so the test drives it
through expt.load_dataset + MedCalcEvaluator directly. The expt module is
loaded once at module scope: its accuracy/sampling helpers are pure, so they
survive sys.modules churn from other benchmark tests in the same process.
"""

from pathlib import Path

import pandas as pd
import pytest

from conftest import CI_TEST_MODEL, load_benchmark_modules, needs_api_key
from secretagent import config
from secretagent.core import implement_via_config
from secretagent.dataset import Case

MEDCALC_DIR = Path(__file__).resolve().parent.parent / "medcalc"
SNAPSHOT = MEDCALC_DIR / "data" / "test.json"

(EXPT,) = load_benchmark_modules(MEDCALC_DIR, "expt")


# ===================================================================
# TestExtractNumber — no LLM
# ===================================================================

class TestExtractNumber:
    def test_numeric_passthrough(self):
        assert EXPT._extract_number(5) == 5.0
        assert EXPT._extract_number(3.14) == 3.14

    def test_plain_string(self):
        assert EXPT._extract_number("42") == 42.0

    def test_answer_tags(self):
        assert EXPT._extract_number("<answer>12.5</answer>") == 12.5

    def test_answer_prefix(self):
        assert EXPT._extract_number("ANSWER: 7") == 7.0

    def test_last_number_in_text(self):
        assert EXPT._extract_number("the dose is 12.5 mg daily") == 12.5

    def test_none_and_exception(self):
        assert EXPT._extract_number(None) is None
        assert EXPT._extract_number("**exception raised**: boom") is None


# ===================================================================
# TestAccuracy — no LLM
# ===================================================================

class TestAccuracy:
    def test_formula_within_tolerance(self):
        # formula-based categories allow 5% tolerance
        acc = EXPT.calculate_accuracy(predicted=105, ground_truth=100, category="lab test")
        assert acc.is_within_tolerance is True
        assert acc.is_exact_match is False

    def test_formula_outside_tolerance(self):
        acc = EXPT.calculate_accuracy(predicted=110, ground_truth=100, category="lab test")
        assert acc.is_within_tolerance is False

    def test_rule_requires_exact(self):
        # rule-based categories require an exact match (5% is not enough)
        acc = EXPT.calculate_accuracy(predicted=105, ground_truth=100, category="risk")
        assert acc.is_within_tolerance is False
        acc = EXPT.calculate_accuracy(predicted=100, ground_truth=100, category="risk")
        assert acc.is_within_tolerance is True
        assert acc.is_exact_match is True

    def test_date_exact_match(self):
        acc = EXPT.calculate_accuracy(
            predicted="08/31/2023", ground_truth="08/31/2023", output_type="date")
        assert acc.is_exact_match is True
        acc = EXPT.calculate_accuracy(
            predicted="09/01/2023", ground_truth="08/31/2023", output_type="date")
        assert acc.is_exact_match is False

    def test_within_limits(self):
        ok = EXPT.calculate_accuracy(
            predicted=50, ground_truth=100, lower_limit=0, upper_limit=60, category="lab test")
        assert ok.is_within_limits is True
        bad = EXPT.calculate_accuracy(
            predicted=80, ground_truth=100, lower_limit=0, upper_limit=60, category="lab test")
        assert bad.is_within_limits is False

    def test_predicted_none(self):
        acc = EXPT.calculate_accuracy(predicted=None, ground_truth=100)
        assert acc.is_within_tolerance is False
        assert acc.absolute_error == float("inf")


# ===================================================================
# TestSampling — no LLM, synthetic cases
# ===================================================================

class TestSampling:
    @staticmethod
    def _cases(n_per_calc):
        return [
            Case(name=f"{calc}_{i}", input_args=("note", "q"),
                 expected_output=1.0, metadata={"calculator_name": calc})
            for calc in ("a", "b")
            for i in range(n_per_calc)
        ]

    def test_stratified_sample_size_and_coverage(self):
        sample = EXPT.stratified_sample(self._cases(10), 6, seed=1)  # 20 -> 6
        assert len(sample) == 6
        calcs = {(c.metadata or {})["calculator_name"] for c in sample}
        assert calcs == {"a", "b"}  # both calculators represented

    def test_stratified_sample_n_exceeds_total(self):
        sample = EXPT.stratified_sample(self._cases(3), 100)  # n >= len -> all
        assert len(sample) == 6

    def test_per_calculator_sample(self):
        sample = EXPT.per_calculator_sample(self._cases(10), 2, seed=1)
        assert len(sample) == 4  # 2 per calculator x 2 calculators


# ===================================================================
# TestDataset — no LLM, reads the offline snapshot (skipped if absent)
# ===================================================================

@pytest.mark.skipif(not SNAPSHOT.exists(),
                    reason="offline data snapshot absent (run `make data`)")
class TestDataset:
    def setup_method(self):
        config.reset()  # ensure no dataset.category_filter is applied

    def test_load_test_snapshot(self):
        ds = EXPT.load_dataset("test")
        assert len(ds.cases) > 0
        case = ds.cases[0]
        assert len(case.input_args) == 2  # (patient note, question)
        assert case.expected_output is not None
        meta = case.metadata or {}
        for key in ("calculator_name", "category", "output_type"):
            assert key in meta


# ===================================================================
# TestIntegration — real pipeline run (simulate strategy)
# ===================================================================

@needs_api_key
@pytest.mark.skipif(not SNAPSHOT.exists(),
                    reason="offline data snapshot absent (run `make data`)")
class TestIntegration:
    def test_simulate_strategy(self, tmp_path):
        config.reset()
        config.configure(
            yaml_file=MEDCALC_DIR / "conf" / "simulate.yaml",
            dotlist=[
                f"llm.model={CI_TEST_MODEL}",
                f"evaluate.result_dir={tmp_path}",
                f"cachier.cache_dir={tmp_path}/llm_cache",  # keep cache out of cwd
                "dataset.split=test",
            ],
        )
        ptools = EXPT.ptools
        implement_via_config(ptools, config.require("ptools"))
        ds = EXPT.load_dataset("test").configure(n=4)
        entry = getattr(ptools, config.get("evaluate.entry_point", "calculate_medical_value"))
        df = pd.read_csv(EXPT.MedCalcEvaluator().evaluate(ds, entry))
        assert "correct" in df.columns