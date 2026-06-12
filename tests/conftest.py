"""Shared test configuration and markers."""

import os
import pytest

from secretagent.core import _INTERFACES

# Model used by integration tests. Override via CI_TEST_MODEL env var
# to run tests against a different provider (e.g. togetherai/deepseek-ai/DeepSeek-V3.1).
CI_TEST_MODEL = os.environ.get('CI_TEST_MODEL', 'gemini/gemini-3.1-flash-lite')


@pytest.fixture(autouse=True)
def _isolate_interfaces():
    """Snapshot the global interface registry and restore it after each test.

    `_INTERFACES` is process-global and `resolve_tools(..., '__all__')`
    enumerates every registered interface. This fixture is defensive
    hygiene: it evicts interfaces a test defines *inside its body* and
    forgets to remove. It does NOT handle module-level registrations
    (those happen at import, so they're already in every test's snapshot
    and survive the restore) — modules that register interfaces at import
    must clean up themselves (see test_evaluate.teardown_module), and tests
    that enumerate '__all__' should select by name rather than assume the
    registry holds only their own interfaces (see test_resolve_tools_all).
    """
    saved = list(_INTERFACES)
    yield
    _INTERFACES[:] = saved


# Together's key is spelled TOGETHER_API_KEY by the `together` SDK (and used
# that way in test_orchestrate_integration); litellm has historically also
# read TOGETHERAI_API_KEY. Accept either so a Together-only setup isn't skipped.
_LLM_KEY_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "TOGETHER_API_KEY",
    "TOGETHERAI_API_KEY",
)


def _has_llm_key():
    """Check if any supported LLM API key is available."""
    return any(os.environ.get(name) for name in _LLM_KEY_ENV_VARS)


def _has_gemini_key():
    return bool(os.environ.get("GEMINI_API_KEY"))


needs_api_key = pytest.mark.skipif(
    not _has_llm_key(),
    reason=f"No LLM API key set (one of: {', '.join(_LLM_KEY_ENV_VARS)})",
)

needs_anthropic_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

needs_gemini_key = pytest.mark.skipif(
    not _has_gemini_key(),
    reason="GEMINI_API_KEY not set",
)
