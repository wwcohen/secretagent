"""Search space definitions for TabMWP benchmark.

Method levels are selected via --config-file (each config sets different
ptools bindings and entry points). The model dimension is a standard
SearchDimension searched via dotlist override.

Follows the MedCalc pattern: outer loop over LEVELS, inner search over models.
"""

from secretagent.optimize.encoder import SearchDimension

# -- Models --

MODELS = [
    "together_ai/deepseek-ai/DeepSeek-V3.1",
    "together_ai/openai/gpt-oss-20b",
    "together_ai/openai/gpt-oss-120b",
    "together_ai/Qwen/Qwen3.5-9B",
    "together_ai/google/gemma-3n-E4B-it",
    # NOTE: Qwen3.5-9B and gemma-3n-E4B-it do not support tool use.
    # react (simulate_pydantic) will fail with these models (scored 0%).
]

# -- Method levels (level name -> config file) --
# Config files from benchmarks/tabmwp/conf/, each sets ptools bindings.

LEVELS = {
    "unstructured_baseline": "conf/unstructured_baseline.yaml",
    "structured_baseline": "conf/structured_baseline.yaml",
    "workflow": "conf/workflow.yaml",
    "pot": "conf/pot.yaml",
    "react": "conf/react.yaml",
}


# -- Search space builder --

def tabmwp_space() -> tuple[list[SearchDimension], list[str]]:
    """Model dimension only; method levels are selected via --config-file."""
    dims = [
        SearchDimension(key="llm.model", values=MODELS),
    ]
    return dims, []
