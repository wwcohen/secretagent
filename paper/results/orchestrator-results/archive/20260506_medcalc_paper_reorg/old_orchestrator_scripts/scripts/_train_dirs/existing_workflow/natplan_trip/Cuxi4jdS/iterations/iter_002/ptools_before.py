"""Task-specific interfaces for NaturalPlan trip planning.

Decomposition derived from LLM reasoning traces:
1. parse_trip_constraints — extract cities, durations, flights, time windows
2. find_valid_route — find city ordering respecting all constraints
3. build_trip_plan — assign day ranges and format itinerary
"""

from secretagent.core import interface


@interface
def parse_trip_constraints(problem_text: str) -> str:
    """Parse a trip-planning problem into structured JSON.

    Args:
        problem_text: The ENTIRE trip-planning problem as a single string
            (total trip days, each city's required stay duration, direct
            flight connections, time-window constraints, etc.). Pass the
            whole problem text as one argument — do NOT split it into
            multiple arguments.

    Returns:
        A JSON string encoding a dict with these keys:
        - total_days: total trip duration (int)
        - cities: dict mapping city name to required stay duration in days
            e.g. {"Helsinki": 5, "Barcelona": 3, "Florence": 5}
        - flights: adjacency list of direct flights
            e.g. {"Helsinki": ["Barcelona"], "Barcelona": ["Helsinki","Florence"]}
        - time_windows: list of time-window constraints, each with keys
            city, earliest_day, latest_day.

    Example:
        >>> parse_trip_constraints("Visit 3 cities over 13 days: Helsinki 5 days, Barcelona 3 days, Florence 5 days. Flights: Helsinki-Barcelona, Barcelona-Florence. Meet a friend in Florence between day 9 and 14.")
        '{"total_days": 13, "cities": {"Helsinki": 5, "Barcelona": 3, "Florence": 5}, "flights": {"Helsinki": ["Barcelona"], "Barcelona": ["Helsinki", "Florence"], "Florence": ["Barcelona"]}, "time_windows": [{"city": "Florence", "earliest_day": 9, "latest_day": 14}]}'
    """


@interface
def find_valid_route(problem_text: str, constraints_json: str) -> str:
    """Find a valid ordering of cities that respects all constraints.

    Args:
        problem_text: The original problem text (same string you passed to
            parse_trip_constraints).
        constraints_json: The JSON STRING output returned by
            parse_trip_constraints. Pass the raw JSON string as-is — do
            NOT parse it into a dict first.

    Returns:
        A JSON string encoding an ordered list of city names (strings).
        The ordering must satisfy:
        - Direct flights exist between consecutive cities.
        - Total stay durations (minus shared-flight days) fit total_days.
        - All time-window constraints are honored.

    Example:
        >>> find_valid_route("...", '{"total_days": 13, "cities": {"Helsinki": 5, ...}, ...}')
        '["Helsinki", "Barcelona", "Florence"]'
    """


@interface
def build_trip_plan(problem_text: str, constraints_json: str, route_json: str) -> str:
    """Assign day ranges to each city and format the day-by-day itinerary.

    Args:
        problem_text: The original problem text.
        constraints_json: The JSON STRING output from parse_trip_constraints.
            Pass the raw JSON string as-is.
        route_json: The JSON STRING output from find_valid_route (a JSON
            array of city names). Pass the raw JSON string as-is.

    Returns:
        A string itinerary beginning with a header line and followed by
        day-range visit lines and flight lines. Flight days count as the
        last day of the departing stay AND the first day of the arriving
        stay.

        Example format:
        'Here is the trip plan for visiting the {N} European cities for {total_days} days:\\n
         **Day 1-5:** Visit Helsinki for 5 days.\\n
         **Day 5:** Fly from Helsinki to Barcelona.\\n
         **Day 5-7:** Visit Barcelona for 3 days.\\n
         ...'

    Example:
        >>> build_trip_plan("...", '{"total_days": 13, ...}', '["Helsinki","Barcelona","Florence"]')
        'Here is the trip plan for visiting the 3 European cities for 13 days:\\n**Day 1-5:** Visit Helsinki for 5 days.\\n**Day 5:** Fly from Helsinki to Barcelona.\\n...'
    """


@interface
def trip_planning(prompt: str) -> str:
    """Solve a trip-planning problem.

    Given a problem describing total trip days, required stay durations
    for each city, direct flights between cities, and any time-window
    constraints, produce a day-by-day itinerary that satisfies all
    constraints.

    Args:
        prompt: The full trip-planning problem as one string.

    Returns:
        A string itinerary in EXACTLY this format:
        - First line: a header that MUST include the phrase
          'European cities for {N} days'
        - Then one line per city visit with '**Day A-B:**' day-range prefix
        - Then one line per flight with '**Day D:** Fly from {City1} to {City2}.'
        Flight days count as the last day of the departing stay AND the
        first day of the arriving stay (overlapping).

    Example:
        'Here is the trip plan for visiting the 3 European cities for 14 days:\\n**Day 1-5:** Visit Helsinki for 5 days.\\n**Day 5:** Fly from Helsinki to Barcelona.\\n**Day 5-9:** Visit Barcelona for 5 days.\\n**Day 9:** Fly from Barcelona to Florence.\\n**Day 9-14:** Visit Florence for 6 days.'
    """
    ...


def trip_workflow(prompt: str) -> str:
    constraints = parse_trip_constraints(prompt)
    route = find_valid_route(prompt, constraints)
    return build_trip_plan(prompt, constraints, route)
