"""Induced ptools for NaturalPlan trip (seed=42).

Auto-generated from results/20260414.042120.trip_react_train_seed42/results.jsonl.
Model: together_ai/deepseek-ai/DeepSeek-V3.
Do not edit — regenerate via generate_induced_configs.py.
"""

from secretagent.core import implement_via
from ptools.ptools_common import _REACT_STATE


@implement_via('simulate')
def _define_problem_and_strategy_impl(prompt: str, focus: str) -> str:
    """
    This function analyzes a trip planning prompt to extract key constraints and requirements,
    identifying critical elements for initial strategy formulation. It focuses on:
    - Required cities and their stay durations
    - Total trip length constraint
    - Flight connectivity from the adjacency list
    - Time-window constraints (if present)
    - Potential scheduling conflicts or challenges

    The response should be structured as a JSON-like string containing:
    - cities: list of cities with stay durations
    - total_days: integer total trip length
    - flights: summary of flight connectivity
    - time_windows: any time-window constraints
    - strategy: initial recommended approach

    Pay special attention to:
    - Hard constraints that cannot be violated
    - Overlapping time windows that may create conflicts
    - Flight availability between required cities
    - Total days matching stay durations plus travel days

    Returns:
    Example output structure:
    {
      "cities": [{"name": "Paris", "stay_duration": 3}, ...],
      "total_days": 21,
      "flights": {"Paris": ["London", "Berlin"], ...},
      "time_windows": {"Vienna": [9, 14]},
      "strategy": "Start with cities having time constraints, then fill remaining days"
    }
    """


def define_problem_and_strategy(focus: str) -> str:
    """Analyze the trip planning problem to identify key constraints, requirements, and initial strategy.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _define_problem_and_strategy_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _search_constraint_details_impl(prompt: str, focus: str) -> str:
    """
    Searches the problem description for specific constraints related to a given focus (e.g., city, time window, duration).

    This function parses the prompt to extract relevant constraint information matching the focus.
    It looks for:
    - Required stay durations for specific cities
    - Time window constraints (e.g., "visit X between day A and day B")
    - Flight availability/connectivity constraints
    - Any other hard constraints mentioned

    The response should be structured as a summary of all constraints found that match the focus,
    including their type, parameters, and any conflicting requirements.

    Agent should pay attention to:
    - Exact time windows and their boundaries
    - Minimum/maximum stay durations
    - Flight connectivity between cities
    - Potential schedule conflicts
    - Hard constraints that cannot be violated

    Returns:
    A structured text summary of constraints found, or "No constraints found" if none match.

    Example return:
    "Constraints for Paris:
    - Must be visited between day 5 and day 10
    - Minimum stay duration: 3 days
    - Direct flights available to: London, Berlin
    - No conflicting constraints detected"
    """


def search_constraint_details(focus: str) -> str:
    """Search for specific constraint details in a trip planning problem description.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _search_constraint_details_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _search_flight_network_impl(prompt: str, focus: str) -> str:
    """
    Searches the flight network data provided in the prompt to find direct flight connections relevant to the focus. The focus can be a specific city (to find all destinations reachable from it) or a specific route (to check if a direct flight exists). The function returns a structured string listing all direct flights from the focused city or confirming/denying the existence of a specific route. The agent should pay attention to the exact city names as given in the adjacency list and note that the absence of a connection might require indirect routing.

    Returns:
    A structured string. If the focus is a city (e.g., 'Paris'), the output lists all direct destinations:
      'Direct flights from Paris: Berlin, London, Rome.'
    If the focus is a specific route (e.g., 'Paris to Berlin'), the output confirms or denies its existence:
      'Direct flight from Paris to Berlin: Yes.'
      'Direct flight from Paris to Madrid: No.'
    """


def search_flight_network(focus: str) -> str:
    """Extracts and analyzes direct flight connections between cities from the provided adjacency list.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _search_flight_network_impl(_REACT_STATE["prompt"], focus)
