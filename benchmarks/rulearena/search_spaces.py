"""Search space definitions for RuleArena benchmark domains.

Two kinds of search space:

  1. Flat (legacy): 1D model-only dims + method outer loop.
     Used by run_pareto.py for exhaustive method x model enumeration.

  2. Modular: per-interface method + model dimensions.
     Used by NSGA-II for multi-objective optimization over the full
     compositional space (individual = complete workflow configuration).

Method overrides match the per-domain Makefiles (airline/, nba/, tax/).
Each domain uses its own top-level interface and workflow functions.
"""

from secretagent.optimize.encoder import SearchDimension

# -- Models --

MODELS = [
    "together_ai/deepseek-ai/DeepSeek-V3",
    "together_ai/deepseek-ai/DeepSeek-V3.1",
    "together_ai/openai/gpt-oss-20b",
    "together_ai/openai/gpt-oss-120b",
    "together_ai/Qwen/Qwen3.5-9B",
    "together_ai/google/gemma-3n-E4B-it",
    # "claude-haiku-4-5-20251001",  # needs Anthropic API key
    # NOTE: Qwen3.5-9B and gemma-3n-E4B-it do not support tool use.
    # react (simulate_pydantic) will fail with these models (scored 0%).
]

# ---------------------------------------------------------------------------
# Top-level method overrides per domain (match Makefiles exactly)
# ---------------------------------------------------------------------------

AIRLINE_METHODS = {
    "structured_baseline": [
        "ptools.compute_airline_answer.method=simulate",
    ],
    "unstructured_baseline": [
        "ptools.compute_airline_answer.method=direct",
        "ptools.compute_airline_answer.fn=ptools.unstructured_workflow",
    ],
    "workflow": [
        "ptools.compute_airline_answer.method=direct",
        "ptools.compute_airline_answer.fn=ptools.airline_workflow",
    ],
    "pot": [
        "ptools.compute_airline_answer.method=program_of_thought",
        "ptools.compute_airline_answer.tools=[ptools.extract_airline_params,ptools.compute_airline_calculator]",
        "ptools.compute_airline_answer.inject_args=true",
        "llm.max_tokens=16384",
    ],
    "react": [
        "ptools.compute_airline_answer.method=simulate_pydantic",
        "ptools.compute_airline_answer.tools=[ptools.extract_airline_params,ptools.compute_airline_calculator]",
    ],
}

NBA_METHODS = {
    "structured_baseline": [
        "ptools.compute_nba_answer.method=simulate",
    ],
    "unstructured_baseline": [
        "ptools.compute_nba_answer.method=direct",
        "ptools.compute_nba_answer.fn=ptools.unstructured_workflow",
    ],
    "workflow": [
        "ptools.compute_nba_answer.method=direct",
        "ptools.compute_nba_answer.fn=ptools.nba_workflow",
    ],
    "pot": [
        "ptools.compute_nba_answer.method=program_of_thought",
        "ptools.compute_nba_answer.inject_args=true",
        "llm.max_tokens=16384",
    ],
    "react": [
        "ptools.compute_nba_answer.method=simulate_pydantic",
        "ptools.compute_nba_answer.tools=[ptools.extract_nba_params]",
    ],
}

TAX_METHODS = {
    "structured_baseline": [
        "ptools.compute_tax_answer.method=simulate",
    ],
    "unstructured_baseline": [
        "ptools.compute_tax_answer.method=direct",
        "ptools.compute_tax_answer.fn=ptools.unstructured_workflow",
    ],
    "workflow": [
        "ptools.compute_tax_answer.method=direct",
        "ptools.compute_tax_answer.fn=ptools.tax_workflow",
    ],
    "pot": [
        "ptools.compute_tax_answer.method=program_of_thought",
        "ptools.compute_tax_answer.tools=[ptools.extract_tax_params,ptools.compute_tax_calculator]",
        "ptools.compute_tax_answer.inject_args=true",
        "llm.max_tokens=16384",
    ],
    "react": [
        "ptools.compute_tax_answer.method=simulate_pydantic",
        "ptools.compute_tax_answer.tools=[ptools.extract_tax_params,ptools.compute_tax_calculator]",
    ],
    "react_two_phase": [
        "ptools.compute_tax_answer.method=direct",
        "ptools.compute_tax_answer.fn=ptools.two_phase_react_workflow",
        "ptools.compute_tax_answer_react.method=simulate_pydantic",
        "ptools.compute_tax_answer_react.tools=[ptools.compute_tax_calculator]",
    ],
}

DOMAIN_METHODS = {
    "airline": AIRLINE_METHODS,
    "nba": NBA_METHODS,
    "tax": TAX_METHODS,
}


# ---------------------------------------------------------------------------
# Flat (legacy) search spaces — model-only, used by run_pareto.py
# ---------------------------------------------------------------------------

def flat_model_space() -> tuple[list[SearchDimension], list[str]]:
    """Single model dimension; methods applied externally as dotlist overrides."""
    return [SearchDimension(key="llm.model", values=MODELS)], []


FLAT_SPACES = {
    "airline": flat_model_space,
    "nba": flat_model_space,
    "tax": flat_model_space,
}

# Backward compat alias
DOMAIN_SPACES = FLAT_SPACES


# ---------------------------------------------------------------------------
# Modular search spaces — per-interface method + model dimensions (NSGA-II)
# ---------------------------------------------------------------------------

def airline_modular_space():
    """Per-interface search space for airline.

    Each interface gets a method gene and a model gene.
    The top-level method gene is "compound" — each value expands to
    multiple dotlist overrides (returned via compound_overrides).

    Returns:
        dims: list of SearchDimension (6 genes)
        compound_overrides: dict mapping dim key -> {value -> [dotlist overrides]}
    """
    dims = [
        # Gene 0: top-level method (compound — needs special decode)
        SearchDimension(
            key="toplevel_method",
            values=list(AIRLINE_METHODS.keys())),
        # Gene 1: global LLM model
        SearchDimension(key="llm.model", values=MODELS),
        # Gene 2: extract method
        SearchDimension(
            key="ptools.extract_airline_params.method",
            values=["simulate_pydantic", "simulate"]),
        # Gene 3: extract model
        SearchDimension(
            key="ptools.extract_airline_params.model",
            values=MODELS),
        # Gene 4: calculator method
        SearchDimension(
            key="ptools.compute_airline_calculator.method",
            values=["direct", "simulate"]),
        # Gene 5: calculator model
        SearchDimension(
            key="ptools.compute_airline_calculator.model",
            values=MODELS),
    ]

    compound_overrides = {
        "toplevel_method": AIRLINE_METHODS,
    }

    return dims, compound_overrides


def nba_modular_space():
    """Per-interface search space for NBA.

    NBA has one sub-interface (extract_nba_params) and no calculator.
    4 genes, 360 total configs.
    """
    dims = [
        SearchDimension(
            key="toplevel_method",
            values=list(NBA_METHODS.keys())),
        SearchDimension(key="llm.model", values=MODELS),
        SearchDimension(
            key="ptools.extract_nba_params.method",
            values=["simulate_pydantic", "simulate"]),
        SearchDimension(
            key="ptools.extract_nba_params.model",
            values=MODELS),
    ]

    compound_overrides = {
        "toplevel_method": NBA_METHODS,
    }

    return dims, compound_overrides


def tax_modular_space():
    """Per-interface search space for tax.

    Tax has two sub-interfaces (extract_tax_params, compute_tax_calculator)
    and 6 top-level methods including react_two_phase.
    6 genes, 5184 total configs.
    """
    dims = [
        SearchDimension(
            key="toplevel_method",
            values=list(TAX_METHODS.keys())),
        SearchDimension(key="llm.model", values=MODELS),
        SearchDimension(
            key="ptools.extract_tax_params.method",
            values=["simulate_pydantic", "simulate"]),
        SearchDimension(
            key="ptools.extract_tax_params.model",
            values=MODELS),
        SearchDimension(
            key="ptools.compute_tax_calculator.method",
            values=["direct", "simulate"]),
        SearchDimension(
            key="ptools.compute_tax_calculator.model",
            values=MODELS),
    ]

    compound_overrides = {
        "toplevel_method": TAX_METHODS,
    }

    return dims, compound_overrides


MODULAR_SPACES = {
    "airline": airline_modular_space,
    "nba": nba_modular_space,
    "tax": tax_modular_space,
}
