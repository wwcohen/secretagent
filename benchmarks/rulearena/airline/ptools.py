"""RuleArena airline domain: baggage fee calculation."""

import re
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

from secretagent.core import interface, implement_via

_DATA_DIR = Path(__file__).parent / "data"


# -- Data models --

class BagItem(BaseModel):
    id: int
    name: str
    size: list[int]  # [length, width, height] in inches
    weight: int       # pounds


class AirlineParams(BaseModel):
    base_price: int = Field(..., description="Ticket price in dollars (no decimals).")
    customer_class: Literal[
        "Basic Economy", "Main Cabin", "Main Plus",
        "Premium Economy", "Business", "First",
    ] = Field(..., description="Travel class — must be one of the six listed values.")
    routine: str = Field(
        ...,
        description=(
            "The non-U.S. country/region of the flight. Use one of: U.S., Canada, "
            "Mexico, Cuba, Haiti, Panama, Colombia, Ecuador, Peru, South America, "
            "Israel, Qatar, Europe, India, China, Japan, South Korea, Hong Kong, "
            "Australia, New Zealand, Puerto Rico. Use 'U.S.' only for fully domestic "
            "flights between two U.S. cities."
        ),
    )
    direction: Literal[0, 1] = Field(
        ...,
        description=(
            "0 if the U.S. city is the place of DEPARTURE (passenger flies FROM the U.S. "
            "to the foreign region); 1 if the U.S. city is the place of ARRIVAL "
            "(passenger flies FROM the foreign region TO the U.S.). For domestic U.S. "
            "flights use 0."
        ),
    )
    bag_list: list[BagItem] = Field(..., description="Checked and carry-on items.")


# -- Interfaces bound via conf.yaml --

@interface
def extract_airline_params(query: str) -> AirlineParams:
    """Extract structured baggage parameters from an airline fee query."""
    ...


@interface
def compute_airline_calculator(params: dict) -> int:
    """Compute airline baggage fee and total ticket cost.

    Pass the dict returned by extract_airline_params directly as params.
    Required keys: base_price, customer_class, routine, direction, bag_list.

    Returns:
        Total cost (ticket price + baggage fees) as integer dollars.
    """


# -- Unstructured (zero-shot) helpers: always bound --

@implement_via('prompt_llm',
               prompt_template_file='prompt_templates/unstructured.txt',
               answer_pattern=None)
def zeroshot_airline(problem_text: str, rules_text: str) -> str:
    ...


def _parse_numeric_answer(llm_output: str) -> float:
    """Extract a dollar amount from an unstructured LLM response.

    Primary: 'total cost is $X' (prompt-compliant format).
    Fallback: last dollar amount in the response - so LLM reasoning
    is still measured when the model ignores the output format.
    Raises ValueError if no amount is found at all.
    """
    matches = re.findall(
        r'total\s+cost\s*(?:is|=|:)\s*\$?([\d,]+(?:\.\d+)?)',
        llm_output, re.IGNORECASE,
    )
    if matches:
        return float(matches[-1].replace(',', ''))
    amounts = re.findall(r'\$\s*([\d,]+(?:\.\d+)?)', llm_output)
    if amounts:
        return float(amounts[-1].replace(',', ''))
    raise ValueError(f"no dollar amount found in LLM output: {llm_output!r}")


# -- Python helpers --

_VALID_REGIONS = {
    "U.S.", "Puerto Rico", "Canada", "Mexico", "Cuba", "Haiti", "Panama",
    "Colombia", "Ecuador", "Peru", "South America", "Israel", "Qatar",
    "Europe", "India", "China", "Japan", "South Korea", "Hong Kong",
    "Australia", "New Zealand",
}

_REGION_FIXES = {
    # Order matters: city tokens come before short abbreviations like "us"
    # (substring of "austin"/"houston") so the substring scan picks the more
    # specific match first.
    "tokyo": "Japan", "osaka": "Japan", "nagoya": "Japan",
    "beijing": "China", "shanghai": "China", "chengdu": "China",
    "wuhan": "China", "guangzhou": "China",
    "seoul": "South Korea", "busan": "South Korea",
    "sydney": "Australia",
    "mumbai": "India",
    "london": "Europe", "paris": "Europe", "berlin": "Europe",
    "barcelona": "Europe", "stockholm": "Europe", "helsinki": "Europe",
    "athens": "Europe", "amsterdam": "Europe",
    "buenos aires": "South America",
    "bogotá": "Colombia", "bogota": "Colombia",
    "port-au-prince": "Haiti",
    "asia": "China", "north america": "U.S.",
    "united states": "U.S.", "domestic": "U.S.", "usa": "U.S.", "us": "U.S.",
}


def _normalize_region(routine: str) -> str:
    if routine in _VALID_REGIONS:
        return routine
    rt_lower = routine.lower().strip()
    fixed = _REGION_FIXES.get(rt_lower)
    if fixed:
        return fixed
    for token, region in _REGION_FIXES.items():
        if token in rt_lower:
            return region
    return "U.S."


_VALID_CLASSES = {
    "Basic Economy", "Main Cabin", "Main Plus", "Premium Economy",
    "Business", "First",
}

_CLASS_FIXES = {
    "first class": "First", "first": "First",
    "business class": "Business", "business": "Business",
    "main plus class": "Main Plus", "main plus": "Main Plus",
    "main cabin class": "Main Cabin", "main cabin": "Main Cabin", "main": "Main Cabin",
    "basic economy class": "Basic Economy", "basic": "Basic Economy",
    "premium economy class": "Premium Economy", "premium": "Premium Economy",
    "economy": "Basic Economy",
}


def _normalize_customer_class(cc: str) -> str:
    if cc in _VALID_CLASSES:
        return cc
    return _CLASS_FIXES.get(cc.lower().strip(), cc)


def _airline_calc_fn(*args, **kw) -> int:
    """Compute airline fee.

    Accepts four calling conventions because this function is invoked by
    code (positional dict, via airline_workflow), pydantic-ai tools
    (observed: positional expansion of AirlineParams fields under gemini),
    and pot-generated code (keyword `params=...` form). `params: dict` in
    the interface signature gives the framework no shape info, so we
    normalize here.
    """
    from calculators.airline import compute_airline_fee
    _KEYS = ["base_price", "customer_class", "routine", "direction", "bag_list"]

    if 'params' in kw and not args:
        raw = kw['params']
    elif len(args) == 1 and not kw:
        raw = args[0]
    elif len(args) == len(_KEYS) and not kw:
        raw = dict(zip(_KEYS, args))
    elif set(kw) == set(_KEYS) and not args:
        raw = dict(kw)
    else:
        raise TypeError(
            f"unexpected arg shape: args={len(args)}, kw={sorted(kw)}")

    if hasattr(raw, 'model_dump'):
        raw = raw.model_dump()
    if not isinstance(raw, dict):
        raise TypeError(
            f"expected dict or pydantic model, got {type(raw).__name__}")

    params = dict(raw)
    params["routine"] = _normalize_region(params.get("routine", "U.S."))
    params["customer_class"] = _normalize_customer_class(
        params.get("customer_class", "Main Cabin"))
    return compute_airline_fee(params)


# -- Top-level interface --

@interface
def compute_airline_answer(problem_text: str, rules_text: str) -> float:
    """Given a passenger's itinerary and baggage details, plus the airline's
    fee rules, compute the total cost (ticket price + baggage fees) in dollars.
    """
    ...


# -- Workflows (bound via conf.yaml as direct implementations) --

def airline_workflow(problem_text: str, rules_text: str) -> float:
    """Handcoded workflow: LLM extracts params, Python computes fee."""
    query = f"RULES:\n{rules_text}\n\nQUERY:\n{problem_text}"
    params = extract_airline_params(query=query)
    return float(compute_airline_calculator(params.model_dump()))


def unstructured_workflow(problem_text: str, rules_text: str) -> float:
    """Zero-shot unstructured workflow: prompt LLM, parse numeric answer."""
    raw = zeroshot_airline(problem_text=problem_text, rules_text=rules_text)
    return _parse_numeric_answer(raw)
