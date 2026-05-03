"""Auto-generated code-distilled implementation for build_trip_plan."""

import json
import re

def build_trip_plan(problem_text, constraints_json, route_info):
    try:
        # Parse constraints JSON - handle potential extra text
        # Try to find a valid JSON object in constraints_json
        constraints = None
        # Try direct parse first
        for candidate in [constraints_json, constraints_json.strip()]:
            try:
                constraints = json.loads(candidate)
                break
            except:
                pass
        
        if constraints is None:
            # Try to extract JSON from the string
            match = re.search(r'\{.*\}', constraints_json, re.DOTALL)
            if match:
                try:
                    constraints = json.loads(match.group())
                except:
                    return None
        
        if constraints is None:
            return None
        
        total_days = constraints["total_days"]
        cities = constraints["cities"]  # dict city -> duration
        flights = constraints.get("flights", {})
        time_windows = constraints.get("time_windows", [])
        
        # Extract route from route_info
        route = None
        
        # Try parsing route_info as a JSON list
        try:
            parsed = json.loads(route_info)
            if isinstance(parsed, list):
                route = parsed
        except:
            pass
        
        # If not a simple list, try to extract route from the reasoning text
        if route is None:
            # Look for a JSON array in route_info
            arrays = re.findall(r'\[([^\[\]]*)\]', route_info)
            for arr_str in reversed(arrays):  # check last ones first
                try:
                    candidate = json.loads('[' + arr_str + ']')
                    if isinstance(candidate, list) and all(isinstance(x, str) for x in candidate):
                        if len(candidate) == len(cities) and all(c in cities for c in candidate):
                            route = candidate
                            break
                except:
                    pass
        
        # If still no route, try to solve it
        if route is None:
            route = _solve_route(cities, flights, time_windows, total_days)
        
        if route is None:
            return None
        
        # Build the trip plan
        num_cities = len(route)
        
        lines = []
        lines.append(f"Here is the trip plan for visiting the {num_cities} European cities for {total_days} days:")
        
        current_day = 1
        for i, city in enumerate(route):
            duration = cities[city]
            start_day = current_day
            end_day = start_day + duration - 1
            
            # Visit line
            lines.append(f"**Day {start_day}-{end_day}:** Visit {city} for {duration} days.")
            
            # Flight line (if not last city)
            if i < num_cities - 1:
                next_city = route[i + 1]
                lines.append(f"**Day {end_day}:** Fly from {city} to {next_city}.")
                current_day = end_day  # shared day
            
        return '\n'.join(lines)
    
    except Exception as e:
        return None


def _solve_route(cities, flights, time_windows, total_days):
    """Solve for a valid route using backtracking."""
    city_names = list(cities.keys())
    n = len(city_names)
    
    # Build time window dict
    tw = {}
    for w in time_windows:
        tw[w["city"]] = (w["earliest_day"], w["latest_day"])
    
    # Try all permutations via backtracking
    def backtrack(path, visited):
        if len(path) == n:
            # Check total days
            day = 1
            for i, city in enumerate(path):
                start = day
                end = start + cities[city] - 1
                if city in tw:
                    if start < tw[city][0] or end > tw[city][1]:
                        return None
                if i < n - 1:
                    day = end  # shared day
                else:
                    if end != total_days:
                        return None
            return list(path)
        
        for city in city_names:
            if city in visited:
                continue
            # Check flight connectivity
            if path:
                last = path[-1]
                if city not in flights.get(last, []):
                    continue
            
            # Compute start/end for this city
            if not path:
                day = 1
            else:
                # Calculate current day
                day = 1
                for i, c in enumerate(path):
                    start = day
                    end = start + cities[c] - 1
                    day = end  # shared
                
            start = day
            end = start + cities[city] - 1
            
            if city in tw:
                if start < tw[city][0] or end > tw[city][1]:
                    continue
            
            # Pruning: end shouldn't exceed total_days
            if end > total_days:
                continue
            
            path.append(city)
            visited.add(city)
            result = backtrack(path, visited)
            if result is not None:
                return result
            path.pop()
            visited.remove(city)
        
        return None
    
    return backtrack([], set())
