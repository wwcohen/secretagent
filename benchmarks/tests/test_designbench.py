"""Lightweight pytest suite for benchmarks/designbench/.

Runs one-example smoke evaluations across all 4 frameworks and verifies
that results are written successfully. Mirrors the integration style used
by other benchmark test modules.

If ``benchmarks/designbench/data/generation/<framework>/`` is missing (dataset
not built), tests use bundled HTML/JSON under
``benchmarks/tests/fixtures/designbench_generation_minimal/`` plus a tiny
synthetic PNG written into a per-test temp dir (see ``expt.load_dataset``'s
``generation_root`` argument).
"""

import os
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

from conftest import CI_TEST_MODEL, needs_api_key
from secretagent import config
from secretagent.core import implement_via_config

DESIGNBENCH_DIR = Path(__file__).resolve().parent.parent / "designbench"
CONF_FILE = DESIGNBENCH_DIR / "conf" / "conf.yaml"
REFINE_LOOP_CONF = DESIGNBENCH_DIR / "conf" / "refine_loop_gemini.yaml"
_MINIMAL_GEN_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "designbench_generation_minimal"
)
# 1x1 RGB PNG (tests add this next to fixture HTML when using bundled minimal data).
_MINI_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de0000000c4944415408d763f8cfc000000301010018dd8db40000000049454e44ae426082"
)


def _import_modules():
    """Import ptools and expt from benchmarks/designbench/ deterministically."""
    from conftest import load_benchmark_modules
    return load_benchmark_modules(DESIGNBENCH_DIR, "ptools", "expt")


def _materialize_minimal_generation_root(tmp_path: Path, src: Path) -> Path:
    """Copy text fixtures into ``tmp_path`` and add a tiny PNG for each item."""
    dst = tmp_path / "designbench_generation_minimal"
    shutil.copytree(src, dst)
    for fw_dir in dst.iterdir():
        if not fw_dir.is_dir():
            continue
        for item_dir in fw_dir.iterdir():
            if not item_dir.is_dir():
                continue
            png = item_dir / f"{item_dir.name}.png"
            png.write_bytes(_MINI_PNG)
    return dst


def _generation_root_for_test(tmp_path: Path, framework: str) -> Path | None:
    """Return ``generation_root`` for ``expt.load_dataset``, or ``None`` for default layout."""
    built = DESIGNBENCH_DIR / "data" / "generation" / framework
    if built.exists():
        return None
    if not _MINIMAL_GEN_FIXTURE.is_dir():
        pytest.skip(
            "DesignBench data not present under benchmarks/designbench/data/generation/ "
            f"for framework={framework}, and bundled minimal fixtures are missing "
            f"({_MINIMAL_GEN_FIXTURE}). Build the dataset (see benchmarks/designbench/) "
            "or restore the fixtures tree."
        )
    return _materialize_minimal_generation_root(tmp_path, _MINIMAL_GEN_FIXTURE)


def _run_eval(tmp_path, framework: str, n: int = 1):
    """Configure and run a tiny DesignBench evaluation."""
    data_root = DESIGNBENCH_DIR / "data" / "generation" / framework
    if not data_root.exists():
        pytest.skip(f"DesignBench dataset not built for framework={framework}; "
                    "run make build inside benchmarks/designbench/")
    generation_root = _generation_root_for_test(tmp_path, framework)
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
            generation_root=generation_root,
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


def test_refine_workflow_config_and_fn_resolve():
    """``refine_loop`` YAML exists; workflow lives on ``ptools`` like other benchmarks."""
    assert REFINE_LOOP_CONF.is_file()
    prev = sys.path[:]
    sys.path.insert(0, str(DESIGNBENCH_DIR))
    try:
        import ptools as designbench_ptools

        assert callable(designbench_ptools.propose_then_refine_loop)
        tail, done = designbench_ptools._strip_refine_done_signal(
            "REFINE_DONE\n```html\n<body></body>\n```"
        )
        assert done and "```html" in tail
        _, not_done = designbench_ptools._strip_refine_done_signal(
            "```html\n<body></body>\n```"
        )
        assert not not_done
    finally:
        sys.path[:] = prev


@needs_api_key
class TestDesignBenchBasics:
    """Integration smoke tests across all DesignBench frameworks."""

    @pytest.mark.parametrize("framework", ["vanilla", "react", "vue", "angular"])
    def test_ptools_smoke(self, tmp_path, framework):
        df = _run_eval(tmp_path, framework=framework, n=1)
        assert len(df) == 1
