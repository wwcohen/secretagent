"""Shared test configuration and markers."""

import os
import pytest

# Model used by integration tests. Override via CI_TEST_MODEL env var
# to run tests against a different provider (e.g. togetherai/deepseek-ai/DeepSeek-V3.1).
CI_TEST_MODEL = os.environ.get('CI_TEST_MODEL', 'claude-haiku-4-5-20251001')


def _has_llm_key():
    """Check if any supported LLM API key is available."""
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("TOGETHERAI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )


def _has_gemini_key():
    return bool(os.environ.get("GEMINI_API_KEY"))


needs_api_key = pytest.mark.skipif(
    not _has_llm_key(),
    reason="No LLM API key set (ANTHROPIC_API_KEY or TOGETHERAI_API_KEY)",
)

needs_anthropic_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

needs_gemini_key = pytest.mark.skipif(
    not _has_gemini_key(),
    reason="GEMINI_API_KEY not set",
)
