"""Maps DEAP integer vectors to/from secretagent dotlist config strings."""

from dataclasses import dataclass, field
from math import prod
from typing import Any


@dataclass
class SearchDimension:
    key: str
    values: list[Any] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.values)


def encode(dims: list[SearchDimension], config: dict[str, Any]) -> list[int]:
    """Map a {key: value} config dict to an integer vector.

    Each element is the index of the config value in the corresponding
    dimension's values list.

    Raises KeyError if a dimension key is missing from config.
    Raises ValueError if a config value is not in the dimension's values.
    """
    vec = []
    for dim in dims:
        val = config[dim.key]
        try:
            vec.append(dim.values.index(val))
        except ValueError:
            raise ValueError(
                f"{dim.key}={val!r} not in {dim.values}"
            )
    return vec


def decode(dims: list[SearchDimension], vec: list[int]) -> list[str]:
    """Map an integer vector to a list of dotlist strings.

    Returns e.g. ["llm.model=gpt-4o", "ptools.foo.method=simulate"].

    Raises IndexError if any index is out of bounds for its dimension.
    """
    if len(vec) != len(dims):
        raise ValueError(
            f"Vector length {len(vec)} != number of dimensions {len(dims)}"
        )
    parts = []
    for dim, idx in zip(dims, vec):
        if idx < 0 or idx >= dim.size:
            raise IndexError(
                f"{dim.key}: index {idx} out of range [0, {dim.size})"
            )
        parts.append(f"{dim.key}={dim.values[idx]}")
    return parts


def decode_modular(
    dims: list[SearchDimension],
    vec: list[int],
    compound_overrides: dict[str, dict[str, list[str]]],
) -> list[str]:
    """Map an integer vector to dotlist strings, expanding compound dimensions.

    Standard dimensions produce one "key=value" string each.
    Compound dimensions (key present in compound_overrides) expand to
    the full list of dotlist overrides for that value.

    Args:
        dims: search dimensions
        vec: integer vector (one index per dimension)
        compound_overrides: {dim_key: {value_name: [dotlist_override, ...]}}
    """
    if len(vec) != len(dims):
        raise ValueError(
            f"Vector length {len(vec)} != number of dimensions {len(dims)}"
        )
    parts: list[str] = []
    for dim, idx in zip(dims, vec):
        if idx < 0 or idx >= dim.size:
            raise IndexError(
                f"{dim.key}: index {idx} out of range [0, {dim.size})"
            )
        value = dim.values[idx]
        if dim.key in compound_overrides:
            parts.extend(compound_overrides[dim.key][value])
        else:
            parts.append(f"{dim.key}={value}")
    return parts


def decode_dict(dims: list[SearchDimension], vec: list[int]) -> dict[str, Any]:
    """Map an integer vector to a {key: value} config dict."""
    if len(vec) != len(dims):
        raise ValueError(
            f"Vector length {len(vec)} != number of dimensions {len(dims)}"
        )
    result = {}
    for dim, idx in zip(dims, vec):
        if idx < 0 or idx >= dim.size:
            raise IndexError(
                f"{dim.key}: index {idx} out of range [0, {dim.size})"
            )
        result[dim.key] = dim.values[idx]
    return result


def space_size(dims: list[SearchDimension]) -> int:
    """Total number of configs in the search space (product of all dim sizes)."""
    if not dims:
        return 0
    return prod(dim.size for dim in dims)


def dim_sizes(dims: list[SearchDimension]) -> list[int]:
    """Return the number of valid values per dimension."""
    return [dim.size for dim in dims]


def modular_space_from_yaml(
    yaml_path: str,
) -> tuple[list[SearchDimension], dict[str, dict[str, list[str]]], dict[str, str]]:
    """Build a modular search space from a YAML definition.

    YAML schema::

        interface: ptools.compute_airline_answer   # optional
        evaluator: evaluator.AirlineEvaluator      # optional

        models:
          - together_ai/deepseek-ai/DeepSeek-V3
          - together_ai/openai/gpt-oss-20b

        methods:
          structured_baseline:
            - ptools.compute_airline_answer.method=simulate
          workflow:
            - ptools.compute_airline_answer.method=direct
            - ptools.compute_airline_answer.fn=ptools.airline_workflow

        sub_interfaces:                            # optional
          ptools.extract_airline_params:
            methods: [simulate_pydantic, simulate]
          ptools.compute_airline_calculator:
            methods: [direct, simulate]

    Returns:
        (dims, compound_overrides, metadata) where metadata has
        optional 'interface' and 'evaluator' keys.
    """
    import yaml
    with open(yaml_path) as f:
        cfg = yaml.safe_load(f)

    models = cfg["models"]
    methods = cfg["methods"]

    dims = [
        SearchDimension(key="toplevel_method", values=list(methods.keys())),
        SearchDimension(key="llm.model", values=models),
    ]

    for iface_key, iface_cfg in cfg.get("sub_interfaces", {}).items():
        dims.append(SearchDimension(
            key=f"{iface_key}.method",
            values=iface_cfg["methods"],
        ))
        dims.append(SearchDimension(
            key=f"{iface_key}.model",
            values=iface_cfg.get("models", models),
        ))

    compound_overrides = {"toplevel_method": methods}

    metadata = {}
    for key in ("interface", "evaluator", "command"):
        if key in cfg:
            metadata[key] = cfg[key]

    return dims, compound_overrides, metadata
