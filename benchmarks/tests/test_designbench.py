"""Lightweight pytest suite for benchmarks/designbench/.

Runs one-example smoke evaluations across all 4 frameworks and verifies
that results are written successfully. Mirrors the integration style used
by other benchmark test modules.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

from conftest import CI_TEST_MODEL, needs_api_key
from secretagent import config
from secretagent.core import implement_via_config

DESIGNBENCH_DIR = Path(__file__).resolve().parent.parent / "designbench"
CONF_FILE = DESIGNBENCH_DIR / "conf" / "conf.yaml"


def _import_modules():
    """Import ptools and expt from benchmarks/designbench/ deterministically."""
    from conftest import load_benchmark_modules
    return load_benchmark_modules(DESIGNBENCH_DIR, "ptools", "expt")


def _run_eval(tmp_path, framework: str, n: int = 1):
    """Configure and run a tiny DesignBench evaluation."""
    data_root = DESIGNBENCH_DIR / "data" / "generation" / framework
    if not data_root.exists():
        pytest.skip(f"DesignBench dataset not built for framework={framework}; "
                    "run make build inside benchmarks/designbench/")
    prev_cwd = os.getcwd()
    try:
        os.chdir(DESIGNBENCH_DIR)
        ptools, expt = _import_modules()

        # Reset global config to avoid cross-test contamination.
        config.reset()

        config.configure(
            yaml_file=str(CONF_FILE),
            dotlist=[
                f"llm.model={CI_TEST_MODEL}",
                f"evaluate.result_dir={tmp_path}",
                f"evaluate.expt_name=test_designbench_{framework}",
                f"dataset.framework={framework}",
                f"dataset.n={n}",
                "benchmark.skip_eval=true",
                "cachier.enable_caching=false",
                # Keep tests provider-agnostic: exercise text pipeline only.
                "ptools.generate_code.method=simulate",
            ],
        )
        config.set_root(DESIGNBENCH_DIR)

        implement_via_config(ptools, config.require("ptools"))
        dataset = expt.load_dataset(
            framework=framework,
            max_reference_chars=config.get("dataset.max_reference_chars"),
        )
        dataset.configure(n=n)
        for case in dataset.cases:
            case.input_kw = {}

        evaluator = expt.DesignBenchEvaluator(
            output_framework=config.get("benchmark.output_framework") or framework,
            skip_eval=bool(config.get("benchmark.skip_eval")),
        )
        interface = getattr(ptools, config.require("evaluate.entry_point"))
        csv_path = evaluator.evaluate(dataset, interface)
        df = pd.read_csv(csv_path)
        assert len(df) == n
        assert "code_path" in df.columns
        return df
    finally:
        os.chdir(prev_cwd)


@needs_api_key
class TestDesignBenchBasics:
    """Integration smoke tests across all DesignBench frameworks."""

    @pytest.mark.parametrize("framework", ["vanilla", "react", "vue", "angular"])
    def test_ptools_smoke(self, tmp_path, framework):
        df = _run_eval(tmp_path, framework=framework, n=1)
        assert len(df) == 1
