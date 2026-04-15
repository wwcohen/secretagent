"""Search space definitions for MedCalc benchmark.

Workflow levels are selected via --config-file (each level differs in
multiple ptools bindings, not a single dotlist key). The model dimension
is a standard SearchDimension searched via dotlist override.
"""

from secretagent.optimize.encoder import SearchDimension

MODELS = [
    "together_ai/deepseek-ai/DeepSeek-V3",
    "together_ai/deepseek-ai/DeepSeek-V3.1",
    "together_ai/openai/gpt-oss-20b",
    "together_ai/openai/gpt-oss-120b",
    "together_ai/Qwen/Qwen3.5-9B",
    "together_ai/google/gemma-3n-E4B-it",
    # NOTE: Qwen3.5-9B and gemma-3n-E4B-it do not support tool use.
    # Levels that use simulate_pydantic will fail with these models (scored 0%).
]

LEVELS = {
    "L0": "conf/baseline.yaml",
    "L1": "conf/simulate.yaml",
    "L2": "conf/distilled.yaml",
    "L3": "conf/pot.yaml",
    "L4": "conf/workflow.yaml",
}


def medcalc_space() -> tuple[list[SearchDimension], list[str]]:
    """Model dimension only; workflow levels are selected via --config-file."""
    dims = [
        SearchDimension(key="llm.model", values=MODELS),
    ]
    fixed = []
    return dims, fixed
