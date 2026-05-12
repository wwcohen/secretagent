"""Task-specific interfaces for NaturalPlan trip planning.

Decomposition derived from LLM reasoning traces:
1. parse_trip_constraints — extract cities, durations, flights, time windows
2. find_valid_route — find city ordering respecting all constraints
3. build_trip_plan — assign day ranges and format itinerary
"""

import re
from secretagent.core import interface


def solve_trip_python(prompt: str) -> str:
    """A pure Python solver that attempts to algorithmically solve the trip."""
    try:
        m_total = re.search(r"visit (\d+) European cities for (\d+) days", prompt)
        if not m_total: return ""
        num_cities = int(m_total.group(1))
        total_days = int(m_total.group(2))
        
        cities = {}
        for m in re.finditer(r"spend (\d+) days in ([A-Z][a-zA-Z]+)", prompt):
            cities[m.group(2)] = int(m.group(1))
        for m in re.finditer(r"stay in ([A-Z][a-zA-Z]+) for (\d+) days", prompt):
            cities[m.group(1)] = int(m.group(2))
        for m in re.finditer(r"visit ([A-Z][a-zA-Z]+) for (\d+) days", prompt):
            if m.group(1) != "European":
                cities[m.group(1)] = int(m.group(2))
                
        time_windows = {}
        for m in re.finditer(r"in ([A-Z][a-zA-Z]+) between day (\d+) and day (\d+)", prompt):
            time_windows[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        for m in re.finditer(r"at ([A-Z][a-zA-Z]+) between day (\d+) and day (\d+)", prompt):
            time_windows[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        for m in re.finditer(r"From day (\d+) to day (\d+).*?in ([A-Z][a-zA-Z]+)", prompt, re.IGNORECASE | re.DOTALL):
            time_windows[m.group(3)] = (int(m.group(1)), int(m.group(2)))
        for m in re.finditer(r"During day (\d+) and day (\d+).*?in ([A-Z][a-zA-Z]+)", prompt, re.IGNORECASE | re.DOTALL):
            time_windows[m.group(3)] = (int(m.group(1)), int(m.group(2)))

        flights_section_match = re.search(r"Here are the cities that have direct flights:\n(.*?)(\n\n|\Z)", prompt, re.DOTALL)
        if not flights_section_match: return ""
            
        flights_section = flights_section_match.group(1)
        flights = {c: [] for c in cities}
        for item in flights_section.split(","):
            item = item.strip().strip(".")
            m_dir = re.search(r"from ([A-Z][a-zA-Z]+) to ([A-Z][a-zA-Z]+)", item)
            if m_dir:
                u, v = m_dir.groups()
                if u in flights and v in flights:
                    flights[u].append(v)
                continue
            m_undir = re.search(r"([A-Z][a-zA-Z]+) and ([A-Z][a-zA-Z]+)", item)
            if m_undir:
                u, v = m_undir.groups()
                if u in flights and v in flights:
                    flights[u].append(v)
                    flights[v].append(u)
                    
        if len(cities) != num_cities:
            return ""
            
        n = num_cities
        iterations = 0
        
        def dfs(current_city, current_day, visited):
            nonlocal iterations
            iterations += 1
            if iterations > 100000:
                return None
                
            if len(visited) == n:
                if current_day == total_days:
                    return [current_city]
                return None
                
            for next_city in sorted(flights[current_city]):
                if next_city not in visited:
                    stay = cities[next_city]
                    arrive_day = current_day
                    depart_day = current_day + stay - 1
                    
                    valid = True
                    if next_city in time_windows:
                        w_start, w_end = time_windows[next_city]
                        if not (arrive_day <= w_start and w_end <= depart_day):
                            valid = False
                    
                    if valid:
                        visited.add(next_city)
                        path = dfs(next_city, depart_day, visited)
                        if path:
                            return [current_city] + path
                        visited.remove(next_city)
            return None

        for start_city in sorted(cities.keys()):
            stay = cities[start_city]
            arrive_day = 1
            depart_day = 1 + stay - 1
            
            valid = True
            if start_city in time_windows:
                w_start, w_end = time_windows[start_city]
                if not (arrive_day <= w_start and w_end <= depart_day):
                    valid = False
                    
            if valid:
                path = dfs(start_city, depart_day, {start_city})
                if path:
                    lines = [f"Here is the trip plan for visiting the {n} European cities for {total_days} days:"]
                    lines.append("")
                    
                    curr_day = 1
                    for i, city in enumerate(path):
                        stay = cities[city]
                        depart_day = curr_day + stay - 1
                        
                        if i == 0:
                            lines.append(f"**Day {curr_day}-{depart_day}:** Arriving in {city} and visit {city} for {stay} days.")
                        else:
                            lines.append(f"**Day {curr_day}-{depart_day}:** Visit {city} for {stay} days.")
                            
                        if i < len(path) - 1:
                            next_city = path[i+1]
                            lines.append(f"**Day {depart_day}:** Fly from {city} to {next_city}.")
                            
                        curr_day = depart_day
                        
                    return "\n".join(lines)
    except Exception:
        pass
    return ""


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
        - flights: adjacency list of direct flights. Treat "from A to B" as ONE-WAY directed (A -> B) and "A and B" as TWO-WAY undirected.
            e.g. {"Helsinki": ["Barcelona"], "Barcelona": ["Helsinki","Florence"]}
        - time_windows: list of time-window constraints, each with keys
            city, earliest_day, latest_day.

    Example:
        >>> parse_trip_constraints("Visit 3 cities over 13 days: Helsinki 5 days, Barcelona 3 days, Florence 5 days. Flights: Helsinki and Barcelona, Barcelona and Florence. Meet a friend in Florence between day 9 and 14.")
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
        stay. The FIRST city visited MUST be formatted as 'Arriving in {City} and visit {City}'.

        Example format:
        'Here is the trip plan for visiting the {N} European cities for {total_days} days:\\n\\n
         **Day 1-5:** Arriving in Helsinki and visit Helsinki for 5 days.\\n
         **Day 5:** Fly from Helsinki to Barcelona.\\n
         **Day 5-9:** Visit Barcelona for 5 days.\\n
         ...'

    Example:
        >>> build_trip_plan("...", '{"total_days": 13, ...}', '["Helsinki","Barcelona","Florence"]')
        'Here is the trip plan for visiting the 3 European cities for 13 days:\\n\\n**Day 1-5:** Arriving in Helsinki and visit Helsinki for 5 days.\\n**Day 5:** Fly from Helsinki to Barcelona.\\n**Day 5-9:** Visit Barcelona for 5 days.\\n**Day 9:** Fly from Barcelona to Florence.\\n**Day 9-13:** Visit Florence for 5 days.'
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
        - Then one line per city visit with '**Day A-B:**' day-range prefix. The FIRST city visited must use 'Arriving in {City} and visit {City}'.
        - Then one line per flight with '**Day D:** Fly from {City1} to {City2}.'
        Flight days count as the last day of the departing stay AND the
        first day of the arriving stay (overlapping).

    Example:
        'Here is the trip plan for visiting the 3 European cities for 13 days:\n\n**Day 1-5:** Arriving in Helsinki and visit Helsinki for 5 days.\n**Day 5:** Fly from Helsinki to Barcelona.\n**Day 5-9:** Visit Barcelona for 5 days.\n**Day 9:** Fly from Barcelona to Florence.\n**Day 9-13:** Visit Florence for 5 days.'
    """
    ...


def trip_workflow(prompt: str) -> str:
    res = solve_trip_python(prompt)
    if res:
        return res
    constraints = parse_trip_constraints(prompt)
    route = find_valid_route(prompt, constraints)
    return build_trip_plan(prompt, constraints, route)

# --- Auto-generated by orchestration_learner --seed-orchestrate ---
def trip_planning_orchestrated_seed(prompt: str) -> str:
    res = solve_trip_python(prompt)
    if res:
        return res
    constraints_json = parse_trip_constraints(prompt)
    route_json = find_valid_route(prompt, constraints_json)
    itinerary = build_trip_plan(prompt, constraints_json, route_json)
    return itinerary