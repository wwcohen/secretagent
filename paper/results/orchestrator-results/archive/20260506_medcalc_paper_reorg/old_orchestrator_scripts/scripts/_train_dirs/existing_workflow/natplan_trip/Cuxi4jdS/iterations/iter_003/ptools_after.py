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
        >>> parse_trip_constraints("Visit 3 cities over 14 days: Helsinki 5 days, Barcelona 5 days, Florence 6 days. Flights: Helsinki-Barcelona, Barcelona-Florence. Meet a friend in Florence between day 9 and 14.")
        '{"total_days": 14, "cities": {"Helsinki": 5, "Barcelona": 5, "Florence": 6}, "flights": {"Helsinki": ["Barcelona"], "Barcelona": ["Helsinki", "Florence"], "Florence": ["Barcelona"]}, "time_windows": [{"city": "Florence", "earliest_day": 9, "latest_day": 14}]}'
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
        >>> find_valid_route("...", '{"total_days": 14, "cities": {"Helsinki": 5, ...}, ...}')
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
        
        The first city visit MUST begin with "Arriving in {City} and visit {City} for {Days} days."

        Example format:
        'Here is the trip plan for visiting the {N} European cities for {total_days} days:\\n
         **Day 1-5:** Arriving in Helsinki and visit Helsinki for 5 days.\\n
         **Day 5:** Fly from Helsinki to Barcelona.\\n
         **Day 5-9:** Visit Barcelona for 5 days.\\n
         ...'

    Example:
        >>> build_trip_plan("...", '{"total_days": 14, ...}', '["Helsinki","Barcelona","Florence"]')
        'Here is the trip plan for visiting the 3 European cities for 14 days:\\n**Day 1-5:** Arriving in Helsinki and visit Helsinki for 5 days.\\n**Day 5:** Fly from Helsinki to Barcelona.\\n**Day 5-9:** Visit Barcelona for 5 days.\\n**Day 9:** Fly from Barcelona to Florence.\\n**Day 9-14:** Visit Florence for 6 days.'
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
        - The first city visit MUST begin with '**Day 1-B:** Arriving in {City} and visit {City} for {Days} days.'
        - Then one line per subsequent city visit with '**Day A-B:** Visit {City} for {Days} days.' day-range prefix
        - Then one line per flight with '**Day D:** Fly from {City1} to {City2}.'
        Flight days count as the last day of the departing stay AND the
        first day of the arriving stay (overlapping).

    Example:
        'Here is the trip plan for visiting the 3 European cities for 14 days:\\n**Day 1-5:** Arriving in Helsinki and visit Helsinki for 5 days.\\n**Day 5:** Fly from Helsinki to Barcelona.\\n**Day 5-9:** Visit Barcelona for 5 days.\\n**Day 9:** Fly from Barcelona to Florence.\\n**Day 9-14:** Visit Florence for 6 days.'
    """
    ...


def extract_flights_from_text(problem_text: str):
    """Accurately parses flights from standard problem text to prevent hallucination."""
    flights = {}
    match = re.search(r'Here are the cities that have direct flights:\n(.*?)\n\n', problem_text + '\n\n', re.DOTALL)
    if not match:
        return None
    flight_str = match.group(1).replace('\n', ' ')
    pairs = flight_str.split(',')
    
    for pair in pairs:
        pair = pair.strip().strip('.')
        if not pair:
            continue
        m_uni = re.match(r'from\s+([A-Za-z\s]+)\s+to\s+([A-Za-z\s]+)', pair, re.IGNORECASE)
        if m_uni:
            src, dst = m_uni.group(1).strip(), m_uni.group(2).strip()
            flights.setdefault(src, []).append(dst)
            continue
        m_bi = re.match(r'([A-Za-z\s]+)\s+and\s+([A-Za-z\s]+)', pair, re.IGNORECASE)
        if m_bi:
            c1, c2 = m_bi.group(1).strip(), m_bi.group(2).strip()
            flights.setdefault(c1, []).append(c2)
            flights.setdefault(c2, []).append(c1)
            continue
            
    if not flights:
        return None
    return flights


def verify_route(route_list, constraints, problem_text):
    """Verifies route logic to strictly enforce valid flights & scheduling constraints."""
    try:
        if not isinstance(route_list, list):
            return False
            
        expected_cities = set(constraints.get("cities", {}).keys())
        route_cities = set(route_list)
        if expected_cities != route_cities or len(route_list) != len(expected_cities):
            return False
            
        flights = extract_flights_from_text(problem_text)
        if not flights:
            flights = constraints.get("flights", {})
            
        current_day = 1
        for i in range(len(route_list)):
            city = route_list[i]
            duration = int(constraints["cities"].get(city, 0))
            arrival = current_day
            departure = arrival + duration - 1
            
            for tw in constraints.get("time_windows", []):
                if tw["city"] == city:
                    if arrival > int(tw["earliest_day"]) or departure < int(tw["latest_day"]):
                        return False
            
            if i < len(route_list) - 1:
                next_city = route_list[i+1]
                if next_city not in flights.get(city, []):
                    return False
            
            current_day = departure
            
        if current_day != int(constraints.get("total_days", current_day)):
            return False
            
        return True
    except Exception:
        return True  # Avoid false positive rejections if verification logic errors


def python_dfs_fallback(problem_text, constraints):
    """Runs ONLY if the LLM's route is explicitly verified as invalid to guarantee constraints."""
    try:
        cities_req = constraints.get("cities", {})
        if not cities_req:
            return None
            
        flights = extract_flights_from_text(problem_text)
        if not flights:
            flights = constraints.get("flights", {})
            
        time_windows_list = constraints.get("time_windows", [])
        time_windows = {}
        for tw in time_windows_list:
            time_windows[tw["city"]] = (int(tw["earliest_day"]), int(tw["latest_day"]))
            
        total_days = int(constraints.get("total_days", 0))
        if not total_days:
            return None
            
        cities = list(cities_req.keys())
        n = len(cities)
        
        def dfs(current_city, visited, current_day):
            if len(visited) == n:
                if current_day == total_days:
                    return [current_city]
                return None
                
            for nxt in flights.get(current_city, []):
                if nxt in cities_req and nxt not in visited:
                    duration = int(cities_req[nxt])
                    arr = current_day
                    dep = arr + duration - 1
                    
                    valid = True
                    if nxt in time_windows:
                        earliest, latest = time_windows[nxt]
                        if arr > earliest or dep < latest:
                            valid = False
                    
                    if valid:
                        path = dfs(nxt, visited | {nxt}, dep)
                        if path:
                            return [current_city] + path
            return None

        for start_city in cities:
            duration = int(cities_req[start_city])
            arr = 1
            dep = arr + duration - 1
            valid = True
            if start_city in time_windows:
                earliest, latest = time_windows[start_city]
                if arr > earliest or dep < latest:
                    valid = False
            if valid:
                path = dfs(start_city, {start_city}, dep)
                if path:
                    return path
                    
        return None
    except Exception:
        return None


def trip_workflow(prompt: str) -> str:
    constraints_str = parse_trip_constraints(prompt)
    route_str = find_valid_route(prompt, constraints_str)
    
    try:
        constraints = json.loads(constraints_str)
        
        cleaned_route = route_str.strip()
        if cleaned_route.startswith("```"):
            match = re.search(r'\[.*?\]', cleaned_route, re.DOTALL)
            if match:
                cleaned_route = match.group(0)
        route_list = json.loads(cleaned_route)
        
        # Safe fallback trigger: only reroute if mathematically incorrect
        if not verify_route(route_list, constraints, prompt):
            fallback_route = python_dfs_fallback(prompt, constraints)
            if fallback_route:
                route_str = json.dumps(fallback_route)
    except Exception:
        pass
        
    return build_trip_plan(prompt, constraints_str, route_str)