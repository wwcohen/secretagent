"""Model comparison wrapped as @interface ptools — FREE (no LLM calls).

These interfaces let pipelines and users query model benchmark,
pricing, and speed data from Artificial Analysis without incurring
any LLM API costs.

Data source: https://artificialanalysis.ai/
"""

from secretagent.core import interface
from secretagent.orchestrate.model_info import (
    lookup_model, format_model_comparison, format_model_summary,
)


@interface
def compare_models(model_a: str, model_b: str) -> str:
    """Compare two LLM models on benchmarks, pricing, and speed.

    Uses cached data from Artificial Analysis.  FREE — no LLM API calls.

    Args:
        model_a: model name in litellm format (e.g. 'together_ai/deepseek-ai/DeepSeek-V3.1')
                 or base name (e.g. 'DeepSeek-V3.1')
        model_b: model name in litellm format or base name

    Returns:
        Human-readable comparison table with benchmarks, pricing, speed.
        Returns an error message if either model is not found.
    """
    info_a = lookup_model(model_a)
    info_b = lookup_model(model_b)
    if info_a is None:
        return f'Model not found in Artificial Analysis data: {model_a}'
    if info_b is None:
        return f'Model not found in Artificial Analysis data: {model_b}'
    return format_model_comparison(info_a, info_b)


@interface
def model_summary(model_name: str) -> str:
    """Get a one-line summary of a model's benchmarks, pricing, and speed.

    Uses cached data from Artificial Analysis.  FREE — no LLM API calls.

    Args:
        model_name: model name in litellm format or base name

    Returns:
        One-line summary or 'not found' message.
    """
    info = lookup_model(model_name)
    if info is None:
        return f'Model not found in Artificial Analysis data: {model_name}'
    return format_model_summary(info)
