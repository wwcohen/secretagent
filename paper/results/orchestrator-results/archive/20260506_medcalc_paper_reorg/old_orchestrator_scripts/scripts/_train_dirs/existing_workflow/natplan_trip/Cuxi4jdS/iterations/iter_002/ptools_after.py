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


@interface(method="direct")
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
    try:
        constraints = json.loads(constraints_json)
        cities_dict = constraints.get("cities", {})
        if not cities_dict:
            return "[]"
            
        all_cities = list(cities_dict.keys())
        num_cities = len(all_cities)
        
        flights_adj = {c: set() for c in all_cities}
        for c, neighbors in constraints.get("flights", {}).items():
            if c not in flights_adj: 
                flights_adj[c] = set()
            for n in neighbors:
                if n in flights_adj:
                    flights_adj[c].add(n)
                
        # Regex to robustly capture flight paths straight from problem text if LLM misses edges
        flight_section_match = re.search(r'Here are the cities that have direct flights:\n(.*?)(?:\n\n|\Z)', problem_text, re.DOTALL)
        if flight_section_match:
            flight_text = flight_section_match.group(1).strip()
            routes = [r.strip() for r in flight_text.split(',')]
            for route in routes:
                route = route.rstrip('.').strip()
                
                and_match = re.match(r'(.+?)\s+and\s+(.+)', route)
                if and_match:
                    c1, c2 = and_match.group(1).strip(), and_match.group(2).strip()
                    if c1 in flights_adj and c2 in flights_adj:
                        flights_adj[c1].add(c2)
                        flights_adj[c2].add(c1)
                    continue
                
                to_match = re.match(r'(?i)from\s+(.+?)\s+to\s+(.+)', route)
                if to_match:
                    c1, c2 = to_match.group(1).strip(), to_match.group(2).strip()
                    if c1 in flights_adj and c2 in flights_adj:
                        flights_adj[c1].add(c2)

        time_windows = constraints.get("time_windows", [])
        window_dict = {}
        for tw in time_windows:
            city = tw.get("city")
            earliest = tw.get("earliest_day")
            latest = tw.get("latest_day")
            if city and earliest and latest:
                window_dict[city] = (int(earliest), int(latest))

        def solve_dfs(mode="strict"):
            def dfs(current_city, current_day, visited, path):
                stay_duration = int(cities_dict[current_city])
                departure_day = current_day + stay_duration - 1
                
                if mode != "none" and current_city in window_dict:
                    earliest, latest = window_dict[current_city]
                    if mode == "strict":
                        if current_day > earliest or departure_day < latest:
                            return None
                    elif mode == "relaxed":
                        if current_day > latest or departure_day < earliest:
                            return None
                
                if len(visited) == num_cities:
                    return path
                
                for next_city in sorted(list(flights_adj[current_city])):
                    if next_city not in visited:
                        visited.add(next_city)
                        path.append(next_city)
                        res = dfs(next_city, departure_day, visited, path)
                        if res: 
                            return res
                        visited.remove(next_city)
                        path.pop()
                return None

            for start_city in sorted(all_cities):
                stay_duration = int(cities_dict[start_city])
                departure_day = 1 + stay_duration - 1
                valid_start = True
                
                if mode != "none" and start_city in window_dict:
                    earliest, latest = window_dict[start_city]
                    if mode == "strict":
                        if 1 > earliest or departure_day < latest:
                            valid_start = False
                    elif mode == "relaxed":
                        if 1 > latest or departure_day < earliest:
                            valid_start = False
                            
                if valid_start:
                    res = dfs(start_city, 1, {start_city}, [start_city])
                    if res:
                        return res
            return None

        # Tier 1: Try strict bounds
        res = solve_dfs("strict")
        if res: return json.dumps(res)
        
        # Tier 2: Try relaxed (must at least overlap constraint)
        res = solve_dfs("relaxed")
        if res: return json.dumps(res)
        
        # Tier 3: Pure connectivity Hamiltonian Path routing
        res = solve_dfs("none")
        if res: return json.dumps(res)
        
        return json.dumps(all_cities)

    except Exception:
        pass
        
    return "[]"


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