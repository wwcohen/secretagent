"""Shared test configuration for benchmark tests.

Re-exports markers and constants from the main test conftest so
benchmark tests can be run from either location.
"""

import importlib
import os
import sys
from pathlib import Path

import pytest

# Model used by integration tests. Override via CI_TEST_MODEL env var.
CI_TEST_MODEL = os.environ.get('CI_TEST_MODEL', 'claude-haiku-4-5-20251001')


def _has_llm_key():
    """Check if any supported LLM API key is available."""
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("TOGETHERAI_API_KEY")
        or os.environ.get("TOGETHER_AI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )


needs_api_key = pytest.mark.skipif(
    not _has_llm_key(),
    reason="No LLM API key set (ANTHROPIC_API_KEY, TOGETHERAI_API_KEY, or GEMINI_API_KEY)",
)

needs_anthropic_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


# ---------------------------------------------------------------------------
# Cross-benchmark import isolation
#
# Each benchmark dir defines top-level module names that collide across
# benchmarks (ptools, expt, evaluator, ...). When multiple benchmark tests
# run in one pytest process, sys.path accumulates all benchmark dirs and
# sys.modules caches stale bare-name resolutions. load_benchmark_modules()
# makes bare-name imports deterministic for the target benchmark.
# ---------------------------------------------------------------------------

_BENCHMARKS_ROOT = Path(__file__).resolve().parent.parent

# Every top-level module name any benchmark defines that could shadow or be
# shadowed by another benchmark. Purged from sys.modules on each isolated
# import so the right file loads. Include benchmark-unique names too so
# stale leftovers from a prior test cannot linger.
_COLLIDING_NAMES = frozenset({
    "ptools", "ptools_common", "ptools_evolved",
    "ptools_murder", "ptools_object", "ptools_team",
    "ptools_calendar", "ptools_meeting", "ptools_trip",
    "ptool_impls", "fhir_tools",
    "expt", "evaluator", "eval_utils",
    "calculators",  # rulearena-only subpackage
})


def _purge_stale_modules():
    """Remove cached benchmark-local modules so imports re-resolve."""
    for name in list(sys.modules):
        top = name.split(".", 1)[0]
        if top in _COLLIDING_NAMES:
            del sys.modules[name]


def load_benchmark_modules(benchmark_dir, *module_names):
    """Import benchmark-local modules from `benchmark_dir` deterministically.

    - Ensures `benchmark_dir` is first on sys.path (ahead of any sibling
      benchmark dir already there).
    - Purges stale colliding module entries from sys.modules.
    - Temporarily changes cwd to `benchmark_dir` during the import call so
      that decorators evaluated at import time (notably
      @implement_via('prompt_llm', prompt_template_file='prompt_templates/...'))
      find their relative paths.

    Returns a tuple of the imported modules in the order requested.
    """
    benchmark_dir = Path(benchmark_dir).resolve()
    bench_str = str(benchmark_dir)
    while bench_str in sys.path:
        sys.path.remove(bench_str)
    sys.path.insert(0, bench_str)
    _purge_stale_modules()
    prev_cwd = os.getcwd()
    try:
        os.chdir(bench_str)
        return tuple(importlib.import_module(n) for n in module_names)
    finally:
        os.chdir(prev_cwd)
