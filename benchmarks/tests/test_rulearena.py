"""Pytest suite for benchmarks/rulearena/ (per-subtask layout).

Rewritten for the migrated per-subtask structure (airline/, nba/, tax/),
modeled on tests/test_natural_plan.py: per-subtask module loading via
conftest.load_benchmark_modules (no os.chdir, no deprecated config.set_root),
per-subtask data/valid.json, and the per-subtask evaluator classes.

Test groups:
  TestConfig      — each subtask conf.yaml loads, dotlist overrides apply
  TestCalculators — airline & tax Python calculators on real records (no LLM)
  TestSchema      — valid.json parses as a Dataset with well-formed cases
  TestMetrics     — AirlineEvaluator / TaxEvaluator / NbaEvaluator scoring
  TestIntegration — structured workflow per subtask on valid examples
                    (needs an API key; results go to tmp_path, not results/)

The structured workflow path (extract_*_params via simulate_pydantic +
compute_*_calculator via direct) is exercised because it avoids the
relative prompt-template resolution that the unstructured path needs.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from conftest import CI_TEST_MODEL, load_benchmark_modules, needs_api_key
from secretagent import config
from secretagent.core import implement_via_config
from secretagent.dataset import Dataset

RULEARENA_DIR = Path(__file__).resolve().parent.parent / "rulearena"

# Per subtask: entry interface, default structured workflow, evaluator class.
SUBTASKS = {
    "airline": {
        "entry": "compute_airline_answer",
        "workflow": "airline_workflow",
        "evaluator": "AirlineEvaluator",
    },
    "tax": {
        "entry": "compute_tax_answer",
        "workflow": "tax_workflow",
        "evaluator": "TaxEvaluator",
    },
    "nba": {
        "entry": "compute_nba_answer",
        "workflow": "nba_workflow",
        "evaluator": "NbaEvaluator",
    },
}


def _conf(task):
    return RULEARENA_DIR / task / "conf" / "conf.yaml"


def _load_subtask(task):
    """Import a subtask's ptools + evaluator (purges sys.path/modules first)."""
    return load_benchmark_modules(RULEARENA_DIR / task, "ptools", "evaluator")


def _first_record(task):
    """First record of a subtask's legacy train.jsonl (carries structured info)."""
    with open(RULEARENA_DIR / task / "data" / "train.jsonl", encoding="utf-8") as f:
        return json.loads(f.readline())


# ===================================================================
# TestConfig — fast, no LLM
# ===================================================================

class TestConfig:
    def setup_method(self):
        config.reset()

    @pytest.mark.parametrize("task", ["airline", "tax", "nba"])
    def test_conf_yaml_loads(self, task):
        config.configure(yaml_file=_conf(task))
        assert config.get("llm.model") is not None
        assert config.get("evaluate.root_interface") == f"ptools.{SUBTASKS[task]['entry']}"
        assert config.get("evaluate.result_dir") is not None

    def test_dotlist_override(self):
        config.configure(yaml_file=_conf("airline"),
                         dotlist=["dataset.n=5", "llm.model=foo"])
        assert config.require("dataset.n") == 5
        assert config.require("llm.model") == "foo"


# ===================================================================
# TestCalculators — no LLM, real records -> sane numeric output
# ===================================================================

class TestCalculators:
    def test_airline_calculator(self):
        _load_subtask("airline")  # airline/ on sys.path, 'calculators' purged
        from calculators.airline import compute_airline_fee
        rec = _first_record("airline")
        fee = compute_airline_fee(rec["info"])
        assert isinstance(fee, (int, float))
        # total cost includes the ticket price, so it can't be below base_price
        assert fee >= rec["info"]["base_price"]

    def test_tax_calculator(self):
        _load_subtask("tax")
        from calculators.tax import compute_tax_fee
        result = compute_tax_fee(_first_record("tax"))
        assert result is not None
        assert isinstance(result, (int, float))

    def test_tax_calculator_sparse_defaults(self):
        """Calculator fills missing schedule fields via _taxpayer_defaults."""
        _load_subtask("tax")
        from calculators.tax import compute_tax_fee
        rec = _first_record("tax")
        sparse = dict(rec)
        sparse["pydantic"] = {"filing_status": rec["pydantic"]["filing_status"]}
        assert compute_tax_fee(sparse) is not None


# ===================================================================
# TestSchema — no LLM, structural checks on the valid split
# ===================================================================

class TestSchema:
    @pytest.mark.parametrize("task", ["airline", "tax", "nba"])
    def test_valid_json_is_dataset(self, task):
        ds = Dataset.model_validate_json(
            (RULEARENA_DIR / task / "data" / "valid.json").read_text(encoding="utf-8")
        )
        assert len(ds.cases) > 0
        for case in ds.cases[:3]:
            assert case.input_args
            assert case.expected_output is not None


# ===================================================================
# TestMetrics — no LLM, per-subtask evaluator logic
# ===================================================================

class TestMetrics:
    def test_airline_evaluator(self):
        _, ev = _load_subtask("airline")
        e = ev.AirlineEvaluator()
        r = e.compare_predictions(100.0, 100.0)
        assert r["correct"] == 1.0 and r["correct_tolerance"] == 1.0
        assert r["failure_mode"] == "none"

        r = e.compare_predictions(100.5, 100.0)
        assert r["correct"] == 0.0            # not an exact match
        assert r["correct_tolerance"] == 1.0  # but within 1%
        assert r["failure_mode"] == "calculation_error"

        assert e.compare_predictions(None, 100.0)["failure_mode"] == "calculation_error"
        exc = "**exception raised**: ValueError('no answer')"
        assert e.compare_predictions(exc, 100.0)["failure_mode"] == "extraction_failure"
        step = "**exception raised**: UsageLimitExceeded(...)"
        assert e.compare_predictions(step, 100.0)["failure_mode"] == "step_limit"

    def test_tax_evaluator(self):
        _, ev = _load_subtask("tax")
        e = ev.TaxEvaluator()
        r = e.compare_predictions(100.5, 100.0)
        assert r["correct"] == 1.0            # within 1% (primary metric)
        assert r["correct_tolerance"] == 0.0  # but not a tight match
        assert e.compare_predictions(102.0, 100.0)["correct"] == 0.0  # 2% > 1%
        exact = e.compare_predictions(100.0, 100.0)
        assert exact["correct"] == 1.0 and exact["correct_tolerance"] == 1.0

    def test_nba_evaluator(self):
        _, ev = _load_subtask("nba")
        e = ev.NbaEvaluator()
        r = e.compare_predictions(1.0, 1.0)
        assert r["correct"] == 1.0 and r["failure_mode"] == "none"
        assert r["tp"] == 1.0
        r = e.compare_predictions(0.0, 1.0)
        assert r["correct"] == 0.0 and r["fn"] == 1.0
        assert e.compare_predictions(None, 1.0)["failure_mode"] == "calculation_error"


# ===================================================================
# TestIntegration — real pipeline run (LLM extraction + Python calculator)
# ===================================================================

def _run_eval(task, tmp_path, n=4):
    """Configure the structured workflow from conf, run it, return the DataFrame.

    Drives the benchmark the way conf.yaml intends: the subtask conf binds the
    extractor (simulate_pydantic) and calculator (direct); we override only the
    DEFAULT entry interface to the structured workflow. Results go to tmp_path
    so the benchmark results/ stays clean. simulate_pydantic needs a
    tool-capable model.
    """
    ptools, ev = _load_subtask(task)
    sub = SUBTASKS[task]
    config.reset()
    config.configure(
        yaml_file=_conf(task),
        dotlist=[
            f"llm.model={CI_TEST_MODEL}",
            f"evaluate.result_dir={tmp_path}",
            f"cachier.cache_dir={tmp_path}/llm_cache",  # keep cache out of cwd
            f"evaluate.expt_name=test_{task}",
            f"ptools.{sub['entry']}.method=direct",
            f"ptools.{sub['entry']}.fn=ptools.{sub['workflow']}",
        ],
    )
    implement_via_config(ptools, config.require("ptools"))
    ds = Dataset.model_validate_json(
        (RULEARENA_DIR / task / "data" / "valid.json").read_text(encoding="utf-8")
    ).configure(n=n)
    evaluator = getattr(ev, sub["evaluator"])()
    df = pd.read_csv(evaluator.evaluate(ds, getattr(ptools, sub["entry"])))
    assert len(df) > 0
    assert "correct" in df.columns
    return df


@needs_api_key
class TestIntegration:
    @pytest.mark.parametrize("task", ["airline", "tax", "nba"])
    def test_structured_workflow(self, task, tmp_path):
        df = _run_eval(task, tmp_path)
        assert "correct" in df.columns