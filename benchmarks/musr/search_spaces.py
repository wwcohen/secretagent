"""Search space definitions for MuSR benchmark domains.

Method levels are selected via --config-file (each level differs in
entry_point and ptools bindings). The model dimension is a standard
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
    # pot levels that use tool-based methods will fail with these models (scored 0%).
]

# -- Method levels per domain (level name -> config file) --

MURDER_LEVELS = {
    "unstructured_baseline": "conf/murder_unstructured_baseline.yaml",
    "workflow": "conf/murder_workflow.yaml",
    "pot": "conf/murder_pot.yaml",
}

OBJECT_LEVELS = {
    "unstructured_baseline": "conf/object_unstructured_baseline.yaml",
    "workflow": "conf/object_workflow.yaml",
    "pot": "conf/object_pot.yaml",
}

TEAM_LEVELS = {
    "unstructured_baseline": "conf/team_unstructured_baseline.yaml",
    "workflow": "conf/team_workflow.yaml",
    "pot": "conf/team_pot.yaml",
}

# -- Search space builders --


def murder_space() -> tuple[list[SearchDimension], list[str]]:
    """Model dimension only; method levels are selected via --config-file."""
    dims = [
        SearchDimension(key="llm.model", values=MODELS),
    ]
    return dims, []


def object_space() -> tuple[list[SearchDimension], list[str]]:
    dims = [
        SearchDimension(key="llm.model", values=MODELS),
    ]
    return dims, []


def team_space() -> tuple[list[SearchDimension], list[str]]:
    dims = [
        SearchDimension(key="llm.model", values=MODELS),
    ]
    return dims, []


DOMAIN_SPACES = {
    "murder": murder_space,
    "object": object_space,
    "team": team_space,
}

DOMAIN_LEVELS = {
    "murder": MURDER_LEVELS,
    "object": OBJECT_LEVELS,
    "team": TEAM_LEVELS,
}
