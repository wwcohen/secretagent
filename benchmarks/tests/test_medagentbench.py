"""Lightweight pytest suite for benchmarks/medagentbench/.

Runs each Makefile strategy on a 2-case slice. Test method names follow
the project-wide scheme used by test_sports_understanding.py and
test_tabmwp.py (unstructured_baseline / structured_baseline / workflow /
pot / react); medagentbench's two unique strategies (codeact and the
orchestrate family) keep their own names.

Strategy -> config mapping:
  test_unstructured_baseline  -> unstructured_baseline.yaml (direct -> medagent_loop)
  test_react                  -> react.yaml                 (simulate_pydantic + tools)
  test_pot                    -> pot.yaml                   (program_of_thought)
  test_codeact                -> codeact.yaml               (direct -> codeact_loop)
  test_orchestrate            -> orchestrate.yaml           (auto-composed pipeline)
  test_orchestrate_evolve     -> orchestrate_evolve.yaml    (compose + evolve)

Prerequisites:
  - An LLM API key (ANTHROPIC_API_KEY or TOGETHER_AI_API_KEY)
  - A MedAgentBench FHIR server reachable on localhost:8080. Start with
        make -C benchmarks/medagentbench docker-start
    or set FHIR_BASE to a custom URL. Tests are skipped when the server
    is not reachable.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

from conftest import needs_api_key, CI_TEST_MODEL

from secretagent import config
from secretagent.core import implement_via_config

MAB_DIR = Path(__file__).resolve().parent.parent / 'medagentbench'
if str(MAB_DIR) not in sys.path:
    sys.path.insert(0, str(MAB_DIR))

FHIR_BASE = os.environ.get('FHIR_BASE', 'http://localhost:8080/fhir/')


def _fhir_reachable() -> bool:
    """Cheap reachability probe — same method the benchmark uses."""
    from conftest import load_benchmark_modules
    (fhir_tools,) = load_benchmark_modules(MAB_DIR, "fhir_tools")
    fhir_tools.set_api_base(FHIR_BASE)
    try:
        return fhir_tools.verify_fhir_server()
    except Exception:
        return False


needs_fhir = pytest.mark.skipif(
    not _fhir_reachable(),
    reason=(
        f'MedAgentBench FHIR server not reachable at {FHIR_BASE}. '
        'Start with: make -C benchmarks/medagentbench docker-start'
    ),
)


def _fresh_expt():
    """Reload medagentbench expt + ptools so each test gets fresh bindings.

    Without this, Interface registrations from a previous test leak into the
    next, and implement_via_config hits a pre-bound interface with stale state.
    Returns (expt, ptools) — caller should not `import ptools` separately,
    since calling load_benchmark_modules again would purge the first reference.
    """
    from conftest import load_benchmark_modules
    return load_benchmark_modules(MAB_DIR, "expt", "ptools")


def _run_eval(tmp_path, config_file, extra_dotlist=None, n=2):
    """Load a config, bind implementations, evaluate n cases, return the df."""
    prev_cwd = os.getcwd()
    try:
        os.chdir(MAB_DIR)
        mab_expt, ptools = _fresh_expt()

        config.configure(
            yaml_file=MAB_DIR / 'conf' / config_file,
            dotlist=[
                f'llm.model={CI_TEST_MODEL}',
                f'orchestrate.model={CI_TEST_MODEL}',
                f'evaluate.result_dir={tmp_path}',
                f'dataset.n={n}',
                f'fhir.api_base={FHIR_BASE}',
                'cachier.enable_caching=False',
            ] + (extra_dotlist or []),
        )
        config.set_root(MAB_DIR)

        dataset = mab_expt.load_dataset(config.get('dataset.version', 'v2'))
        dataset.configure(
            shuffle_seed=config.get('dataset.shuffle_seed'),
            n=n,
        )
        implement_via_config(ptools, config.require('ptools'))

        evaluator = mab_expt.MedAgentBenchEvaluator(FHIR_BASE)
        csv_path = evaluator.evaluate(dataset, ptools.solve_medical_task)
        df = pd.read_csv(csv_path)
        assert len(df) == n
        assert 'correct' in df.columns
        return df
    finally:
        os.chdir(prev_cwd)


@needs_api_key
@needs_fhir
class TestBasics:
    """Integration tests for the 5 base strategies, 2 examples each."""

    def test_unstructured_baseline(self, tmp_path):
        df = _run_eval(tmp_path, 'unstructured_baseline.yaml')
        assert 'correct' in df.columns

    def test_react(self, tmp_path):
        df = _run_eval(tmp_path, 'react.yaml')
        assert 'correct' in df.columns

    def test_pot(self, tmp_path):
        df = _run_eval(tmp_path, 'pot.yaml')
        assert 'correct' in df.columns

    def test_codeact(self, tmp_path):
        df = _run_eval(tmp_path, 'codeact.yaml')
        assert 'correct' in df.columns

    def test_orchestrate(self, tmp_path):
        # orchestrate composes a pipeline at bind-time via LLM; skip if
        # CI_TEST_MODEL is too weak to produce runnable code. Haiku usually
        # does fine for this 2-case smoke test.
        df = _run_eval(tmp_path, 'orchestrate.yaml')
        assert 'correct' in df.columns


@needs_api_key
@needs_fhir
class TestOrchestrateEvolve:
    """End-to-end test for orchestrate-evolve on a minimal config.

    This path composes a workflow, picks a simulate ptool to evolve, runs
    one generation of LLM-proposed variants, then evaluates. It is slower
    than TestBasics and uses more API credits.
    """

    def test_orchestrate_evolve(self, tmp_path):
        prev_cwd = os.getcwd()
        try:
            os.chdir(MAB_DIR)
            mab_expt, ptools = _fresh_expt()

            config.configure(
                yaml_file=MAB_DIR / 'conf' / 'orchestrate_evolve.yaml',
                dotlist=[
                    f'llm.model={CI_TEST_MODEL}',
                    f'orchestrate.model={CI_TEST_MODEL}',
                    f'improve.model={CI_TEST_MODEL}',
                    f'evaluate.result_dir={tmp_path}',
                    f'fhir.api_base={FHIR_BASE}',
                    'dataset.n=2',
                    'improve.population_size=1',
                    'improve.n_generations=1',
                    'improve.train_per_task=1',
                    'cachier.enable_caching=False',
                ],
            )
            config.set_root(MAB_DIR)

            dataset = mab_expt.load_dataset(config.get('dataset.version', 'v2'))
            dataset.configure(shuffle_seed=42, n=2)
            implement_via_config(ptools, config.require('ptools'))

            evaluator = mab_expt.MedAgentBenchEvaluator(FHIR_BASE)
            csv_path = evaluator.evaluate(dataset, ptools.solve_medical_task)
            df = pd.read_csv(csv_path)
            assert len(df) == 2
            assert 'correct' in df.columns
        finally:
            os.chdir(prev_cwd)
