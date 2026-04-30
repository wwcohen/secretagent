"""Induced ptools for NaturalPlan meeting (seed=42).

Auto-generated from results/20260414.033600.meeting_react_train_seed42/results.jsonl.
Model: together_ai/deepseek-ai/DeepSeek-V3.
Do not edit — regenerate via generate_induced_configs.py.
"""

from secretagent.core import implement_via
from ptools.ptools_common import _REACT_STATE


@implement_via('simulate')
def _define_meeting_problem_impl(prompt: str, focus: str) -> str:
    """
    Analyzes a meeting planning problem description to extract key constraints and structure them for optimization.

    Extracts:
    - Starting location and time
    - Friends' locations, availability windows, and minimum meeting durations
    - Travel time matrix between all locations
    - Any additional constraints or preferences

    Returns a structured JSON-like string containing:
    {
      "start": {"location": str, "time": str},
      "friends": [
        {"name": str, "location": str, "window_start": str, "window_end": str, "min_duration": int}
      ],
      "travel_times": {
        "location1-location2": int,
        ...
      }
    }

    Pay attention to:
    - Exact time formats (AM/PM, 24-hour)
    - Window boundaries (inclusive/exclusive)
    - Minimum duration requirements
    - Travel time symmetry (A→B may differ from B→A)
    - All possible location pairs in the travel matrix

    Returns:
    Example output structure:
    {
      "start": {"location": "Fisherman's Wharf", "time": "9:00AM"},
      "friends": [
        {"name": "Michelle", "location": "Bayview", "window_start": "7:45PM", "window_end": "9:15PM", "min_duration": 90},
        {"name": "James", "location": "Embarcadero", "window_start": "3:45PM", "window_end": "5:15PM", "min_duration": 75}
      ],
      "travel_times": {
        "Fisherman's Wharf-Embarcadero": 8,
        "Fisherman's Wharf-Bayview": 26,
        "Embarcadero-Bayview": 21,
        "Bayview-Embarcadero": 19,
        "Embarcadero-Fisherman's Wharf": 6,
        "Bayview-Fisherman's Wharf": 25
      }
    }
    """


def define_meeting_problem(focus: str) -> str:
    """Extracts and structures meeting planning constraints from a problem description.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _define_meeting_problem_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _request_travel_times_impl(prompt: str, focus: str) -> str:
    """
    Extracts and returns travel time information between locations from the provided travel-time matrix.
    The function focuses on travel times relevant to the specified focus (e.g., a person, location, or constraint).
    The agent should pay attention to:
    - Symmetry of travel times (if not provided, assume symmetric)
    - Travel time units (consistent with meeting duration)
    - Direct connections vs. multi-hop routes (if matrix includes indirect paths)
    - Any constraints affecting travel (e.g., traffic patterns, time-dependent routes)

    Returns:
    A structured string listing travel times for pairs involving the focus. If focus is a person, returns times from their location to others. If focus is a location, returns times from it to all other locations. If focus is general (e.g., "all"), returns the full travel-time matrix.

    Example output for focus="Alice":
    {
      "travel_times": {
        "Alice->Bob": 15,
        "Alice->Charlie": 20,
        "Alice->David": 25
      }
    }
    """


def request_travel_times(focus: str) -> str:
    """Requests travel time information between specified locations to evaluate meeting feasibility.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _request_travel_times_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _propose_meeting_schedule_impl(prompt: str, focus: str) -> str:
    """
    Extracts meeting constraints from the problem description and proposes an optimal schedule.

    Parses:
    - Starting location and time
    - Friend locations, availability windows, and minimum meeting durations
    - Travel time matrix between locations

    Reasoning:
    - Prioritizes meeting as many friends as possible
    - Ensures meetings occur within specified availability windows
    - Accounts for travel time between locations
    - Ensures minimum meeting duration requirements are met
    - Handles waiting time before meetings if needed
    - Optimizes schedule to maximize total meetings

    Returns:
    A structured schedule with:
    - Start time and location
    - Sequence of meetings with arrival/departure times
    - Travel segments with durations
    - Total meeting time for each friend
    - Confirmation that minimum durations are met

    Example output structure:
    \"\"\"
    Start at [location] at [time].
    Travel to [location] ([duration] min), arrive at [time].
    Meet [friend] from [start] to [end] ([duration] min).
    Travel to [location] ([duration] min), arrive at [time].
    ...
    This schedule allows meeting [number] friends for their minimum durations.
    \"\"\"

    Note: Focus parameter can specify a particular friend, location, or constraint
    to prioritize in the scheduling optimization.
    """


def propose_meeting_schedule(focus: str) -> str:
    """Proposes an optimal meeting schedule that maximizes the number of friends met within their availability windows while accounting for travel time.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _propose_meeting_schedule_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _verify_constraints_impl(prompt: str, focus: str) -> str:
    """
    This function analyzes a meeting planning prompt to extract and validate constraints related to a specific focus. It searches for all mentions of the focus (e.g., a person's name, a location) and extracts associated constraints such as availability windows, minimum meeting durations, and travel times. The function then performs basic validation, checking for the existence of the focus and ensuring its constraints are well-defined (e.g., time windows are valid, durations are positive).

    The response is structured as a plain text summary containing:
    1. A confirmation of whether the focus was found.
    2. A list of all constraints directly associated with the focus.
    3. A list of any potential constraint violations or missing information.
    4. Any other relevant constraints (e.g., travel times) that involve the focus.

    Attention should be paid to:
    - Ensuring the focus (e.g., a friend's name) is correctly identified in the prompt.
    - Correctly parsing time windows (start and end times) and durations.
    - Identifying hard constraints that cannot be violated.
    - Noting any dependencies or conflicts with other parts of the schedule.

    Returns:
    A structured plain text string summarizing the findings.

    Example output for focus='Betty':
    "Focus 'Betty' found. Constraints: Availability from 09:00 to 11:00, minimum meeting duration 30 minutes. Located at CityA. Travel time from your location (Home) to CityA is 15 minutes. No constraint violations detected."
    """


def verify_constraints(focus: str) -> str:
    """Extracts and validates constraints related to a specific focus (person, location, time, etc.) within a meeting planning problem.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _verify_constraints_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _analyze_constraints_and_requirements_impl(prompt: str, focus: str) -> str:
    """
    Analyzes the constraints and requirements for scheduling meetings with friends.

    This function parses the problem description to extract:
    - Starting location and time
    - List of friends with their locations, availability windows, and minimum meeting durations
    - Travel time matrix between locations
    - Any other scheduling constraints mentioned

    The function focuses on the specified aspect (friend, location, constraint type)
    and evaluates feasibility considering:
    - Arrival/departure times within availability windows
    - Minimum meeting duration requirements
    - Travel times between locations
    - Potential schedule conflicts

    Returns:
    A structured text analysis containing:
    - List of identified constraints
    - Analysis of the focused aspect
    - Timeline calculations for potential meetings
    - Feasibility assessment for meeting the focused friend/constraint
    - Any identified conflicts or limitations

    Example return structure:
    \"\"\"
    Constraints Analysis:
    - Start: Chinatown at 9:00AM
    - Friends: Anthony (Financial District, 10:00AM-12:00PM, 60 min)
    - Travel times: Chinatown→Financial District: 15 min

    Focus: Anthony
    - Earliest arrival: 9:15AM (15 min travel)
    - Meeting window: 10:00AM-12:00PM
    - Minimum duration: 60 min
    - Feasible meeting: Arrive 10:00AM, depart 11:00AM
    - Total meeting time: 60 minutes
    \"\"\"
    """


def analyze_constraints_and_requirements(focus: str) -> str:
    """Analyzes temporal constraints, travel times, and availability windows to determine feasible meeting schedules.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _analyze_constraints_and_requirements_impl(_REACT_STATE["prompt"], focus)
