"""Task-specific interfaces for NaturalPlan trip planning.

Decomposition derived from LLM reasoning traces:
1. parse_trip_constraints — extract cities, durations, flights, time windows
2. find_valid_route — find city ordering respecting all constraints
3. build_trip_plan — assign day ranges and format itinerary
"""

import json
import re
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


def fix_flights_in_constraints(problem_text: str, constraints_json: str) -> str:
    """Uses a safe regex parser to correct hallucinated bidirectional flights."""
    try:
        if "```json" in constraints_json:
            constraints_json = constraints_json.split("```json")[1].split("```")[0].strip()
        elif "```" in constraints_json:
            constraints_json = constraints_json.split("```")[1].split("```")[0].strip()
            
        c_dict = json.loads(constraints_json)
        
        if "Here are the cities that have direct flights:" in problem_text:
            flights_str = problem_text.split("Here are the cities that have direct flights:")[1].strip()
            flights_str = flights_str.split("\n\n")[0].strip()
            flights_str = flights_str.split("Find a trip plan")[0].strip()
            
            if flights_str.endswith('.'): 
                flights_str = flights_str[:-1]
            
            real_flights = {}
            for part in flights_str.split(','):
                part = part.strip()
                if part.startswith("from "):
                    m = re.search(r"from\s+([A-Za-z\s\-]+)\s+to\s+([A-Za-z\s\-]+)", part)
                    if m:
                        u, v = m.group(1).strip(), m.group(2).strip()
                        real_flights.setdefault(u, []).append(v)
                elif " and " in part:
                    m = re.search(r"([A-Za-z\s\-]+)\s+and\s+([A-Za-z\s\-]+)", part)
                    if m:
                        u, v = m.group(1).strip(), m.group(2).strip()
                        real_flights.setdefault(u, []).append(v)
                        real_flights.setdefault(v, []).append(u)
                        
            if real_flights:
                for k in real_flights:
                    real_flights[k] = list(set(real_flights[k]))
                c_dict["flights"] = real_flights
                return json.dumps(c_dict)
                
    except Exception:
        pass
        
    return constraints_json


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
        - ALL cities listed in the constraints MUST be visited exactly once. Do not omit any cities.
        - Direct flights exist between consecutive cities. Pay STRICT attention to unidirectional flights ('from A to B' means A -> B ONLY).
        - Total stay durations (minus shared-flight days) fit total_days.
        - All time-window constraints are honored exactly. For example, if a city has a window of earliest_day 8 and latest_day 9, your arrival day MUST be 8 and departure day MUST be 9.

    Example:
        >>> find_valid_route("...", '{"total_days": 13, "cities": {"Helsinki": 5, ...}, ...}')
        '["Helsinki", "Barcelona", "Florence"]'
    """


@interface(method="direct")
def build_trip_plan(problem_text: str, constraints_json: str, route_json: str) -> str:
    """Assign day ranges to each city and format the day-by-day itinerary."""
    try:
        if "```json" in constraints_json:
            constraints_json = constraints_json.split("```json")[1].split("```")[0].strip()
        elif "```" in constraints_json:
            constraints_json = constraints_json.split("```")[1].split("```")[0].strip()
            
        if "```json" in route_json:
            route_json = route_json.split("```json")[1].split("```")[0].strip()
        elif "```" in route_json:
            route_json = route_json.split("```")[1].split("```")[0].strip()

        constraints = json.loads(constraints_json)
        route = json.loads(route_json)
        
        if isinstance(route, dict) and "route" in route:
            route = route["route"]
            
        if not isinstance(route, list):
            match = re.search(r'\[.*?\]', route_json, re.DOTALL)
            if match:
                route = json.loads(match.group(0))
            else:
                return f"Error: route is not a list. Got: {route_json}"
                
        total_days = constraints.get("total_days", 0)
        cities = constraints.get("cities", {})
        
        lines = []
        lines.append(f"Here is the trip plan for visiting the {len(route)} European cities for {total_days} days:")
        lines.append("")
        
        current_day = 1
        for i, city in enumerate(route):
            stay = cities.get(city, 1)
            try:
                stay = int(stay)
            except ValueError:
                stay = 1
                
            end_day = current_day + stay - 1
            
            if i == 0:
                lines.append(f"**Day {current_day}-{end_day}:** Arriving in {city} and visit {city} for {stay} days.")
            else:
                lines.append(f"**Day {current_day}-{end_day}:** Visit {city} for {stay} days.")
                
            if i < len(route) - 1:
                next_city = route[i+1]
                lines.append(f"**Day {end_day}:** Fly from {city} to {next_city}.")
                current_day = end_day
                
        return "\n".join(lines)
    except Exception as e:
        return f"Here is the trip plan for visiting the European cities:\nError: {str(e)}"


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
        'Here is the trip plan for visiting the 3 European cities for 14 days:\n\n**Day 1-5:** Arriving in Helsinki and visit Helsinki for 5 days.\n**Day 5:** Fly from Helsinki to Barcelona.\n**Day 5-9:** Visit Barcelona for 5 days.\n**Day 9:** Fly from Barcelona to Florence.\n**Day 9-14:** Visit Florence for 6 days.'
    """
    ...


def trip_workflow(prompt: str) -> str:
    constraints = parse_trip_constraints(prompt)
    constraints = fix_flights_in_constraints(prompt, constraints)
    route = find_valid_route(prompt, constraints)
    return build_trip_plan(prompt, constraints, route)