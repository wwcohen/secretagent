"""Task-specific interfaces for NaturalPlan trip planning.

Decomposition derived from LLM reasoning traces:
1. parse_trip_constraints — extract cities, durations, flights, time windows
2. find_valid_route — find city ordering respecting all constraints (Pure Python)
3. build_trip_plan — assign day ranges and format itinerary (Pure Python)
"""

from secretagent.core import interface
import json
import re

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
    """Find a valid ordering of cities that respects all constraints deterministically."""
    try:
        c = json.loads(constraints_json)
    except:
        return "[]"
        
    cities_dict = c.get("cities", {})
    all_cities = list(cities_dict.keys())
    llm_flights = c.get("flights", {})
    time_windows = c.get("time_windows", [])
    
    # Deterministic flight extraction to perfectly honor unidirectional constraints ("from A to B")
    match = re.search(r"direct flights:\s*(.*?)\.?\n\nFind a trip plan", problem_text, re.DOTALL | re.IGNORECASE)
    if match:
        flights = {}
        flight_str = match.group(1).replace('\n', ' ').strip()
        pairs = [x.strip() for x in flight_str.split(',')]
        for pair in pairs:
            if " and " in pair:
                parts = pair.split(" and ", 1)
                if len(parts) == 2:
                    a, b = parts[0].strip(), parts[1].strip()
                    flights.setdefault(a, set()).add(b)
                    flights.setdefault(b, set()).add(a)
            elif pair.startswith("from ") and " to " in pair:
                parts = pair[5:].split(" to ", 1)
                if len(parts) == 2:
                    a, b = parts[0].strip(), parts[1].strip()
                    flights.setdefault(a, set()).add(b)
        flights = {k: list(v) for k, v in flights.items()}
    else:
        flights = llm_flights
        
    windows = {}
    for tw in time_windows:
        city = tw.get("city")
        e = tw.get("earliest_day")
        l = tw.get("latest_day")
        if city and e is not None and l is not None:
            if city not in windows:
                windows[city] = []
            try:
                windows[city].append((int(e), int(l)))
            except:
                pass
                
    def is_last_city_valid(route):
        current_day = 1
        for city in route:
            stay = cities_dict.get(city, 1)
            try:
                stay = int(stay)
            except:
                stay = 1
            end_day = current_day + stay - 1
            
            # Only prune on the latest appended city
            if city == route[-1]:
                if city in windows:
                    for (e, l) in windows[city]:
                        if not (current_day <= e and end_day >= l):
                            return False
                return True
            current_day = end_day
        return True

    def dfs(current_city, visited, route):
        if len(route) == len(all_cities):
            return list(route)
            
        neighbors = flights.get(current_city, [])
        for nxt in neighbors:
            if nxt not in visited and nxt in cities_dict:
                visited.add(nxt)
                route.append(nxt)
                if is_last_city_valid(route):
                    res = dfs(nxt, visited, route)
                    if res:
                        return res
                route.pop()
                visited.remove(nxt)
        return None

    # Search for Hamiltonian Path matching all windows
    for start_city in sorted(all_cities):
        visited = {start_city}
        route = [start_city]
        if not is_last_city_valid(route):
            continue
        res = dfs(start_city, visited, route)
        if res:
            return json.dumps(res)
            
    return json.dumps(all_cities)

@interface(method="direct")
def build_trip_plan(problem_text: str, constraints_json: str, route_json: str) -> str:
    """Assign day ranges to each city and format the day-by-day itinerary directly."""
    try:
        constraints = json.loads(constraints_json)
        route = json.loads(route_json)
    except:
        return ""
        
    if not route:
        return ""
        
    cities = constraints.get("cities", {})
    
    # Calculate exact total days natively 
    calculated_days = 1
    for c in route:
        stay = cities.get(c, 1)
        try:
            stay = int(stay)
        except:
            stay = 1
        calculated_days = calculated_days + stay - 1
        
    total_days = constraints.get("total_days", 0)
    try:
        total_days = int(total_days)
    except:
        total_days = 0
    if total_days == 0:
        total_days = calculated_days
        
    num_cities = len(route)
    
    lines = []
    lines.append(f"Here is the trip plan for visiting the {num_cities} European cities for {total_days} days:")
    lines.append("")
    
    current_day = 1
    for i, city in enumerate(route):
        stay = cities.get(city, 1)
        try:
            stay = int(stay)
        except:
            stay = 1
            
        end_day = current_day + stay - 1
        
        if i == 0:
            lines.append(f"**Day {current_day}-{end_day}:** Arriving in {city} and visit {city} for {stay} days.")
        else:
            lines.append(f"**Day {current_day}-{end_day}:** Visit {city} for {stay} days.")
            
        if i < len(route) - 1:
            lines.append(f"**Day {end_day}:** Fly from {city} to {route[i+1]}.")
            
        current_day = end_day
        
    return "\n".join(lines)

@interface(method="direct")
def trip_planning(prompt: str) -> str:
    """Solve a trip-planning problem natively."""
    return trip_workflow(prompt)

def trip_workflow(prompt: str) -> str:
    constraints = parse_trip_constraints(prompt)
    route = find_valid_route(prompt, constraints)
    return build_trip_plan(prompt, constraints, route)