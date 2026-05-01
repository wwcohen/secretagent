"""Auto-generated code-distilled implementation for build_trip_plan."""

import json
import re

def build_trip_plan(problem_text, constraints_json_str, route_str):
    # Try to extract the JSON containing the constraints from constraints_json_str
    start_idx = constraints_json_str.find('{')
    end_idx = constraints_json_str.rfind('}')
    if start_idx != -1 and end_idx != -1 and start_idx <= end_idx:
        try:
            data = json.loads(constraints_json_str[start_idx:end_idx+1])
        except json.JSONDecodeError:
            return None
    else:
        return None

    cities_info = data.get("cities", {})
    flights = data.get("flights", {})
    time_windows = data.get("time_windows", [])
    total_days = data.get("total_days", 0)
    
    if not cities_info:
        return None
        
    city_names = list(cities_info.keys())
    n = len(city_names)
    
    # Store time windows in an easily queryable dictionary
    tw_map = {}
    for tw in time_windows:
        tw_map[tw["city"]] = (tw["earliest_day"], tw["latest_day"])
        
    valid_route = None
    
    # Try to parse the route_str array if the LLM provided it
    try:
        for match in re.finditer(r'\[.*?\]', route_str, re.DOTALL):
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list) and len(parsed) == n and set(parsed) == set(city_names):
                    valid = True
                    cd = 1
                    for i in range(n):
                        c = parsed[i]
                        stay = cities_info[c]
                        ed = cd + stay - 1
                        
                        # Validate against time windows
                        if c in tw_map:
                            if cd < tw_map[c][0] or ed > tw_map[c][1]:
                                valid = False
                                break
                        
                        # Validate flights between cities
                        if i < n - 1:
                            if parsed[i+1] not in flights.get(c, []):
                                valid = False
                                break
                        cd = ed
                    
                    if valid and cd == total_days:
                        valid_route = parsed
                        break
            except Exception:
                continue
    except Exception:
        pass

    # If parsing a valid route string failed (e.g., text generation was truncated), fall back to DFS 
    if not valid_route:
        def backtrack(current_city, visited, current_day, path):
            stay = cities_info[current_city]
            end_day = current_day + stay - 1
            
            # Check time constraints for the current city
            if current_city in tw_map:
                earliest, latest = tw_map[current_city]
                if current_day < earliest or end_day > latest:
                    return None
                    
            if len(visited) == n:
                if end_day == total_days:
                    return path
                return None
                
            # Explore valid neighbor cities
            for nxt in flights.get(current_city, []):
                if nxt not in visited:
                    res = backtrack(nxt, visited | {nxt}, end_day, path + [nxt])
                    if res:
                        return res
            return None

        # Try to find a valid route starting from any of the cities
        for start_city in city_names:
            res = backtrack(start_city, {start_city}, 1, [start_city])
            if res:
                valid_route = res
                break
                
    if not valid_route:
        return None
        
    # Build the correctly formatted output string
    lines = []
    lines.append(f"Here is the trip plan for visiting the {n} European cities for {total_days} days:")
    
    current_day = 1
    for i in range(len(valid_route)):
        city = valid_route[i]
        stay = cities_info[city]
        end_day = current_day + stay - 1
        
        lines.append(f"**Day {current_day}-{end_day}:** Visit {city} for {stay} days.")
        
        if i < len(valid_route) - 1:
            next_city = valid_route[i+1]
            lines.append(f"**Day {end_day}:** Fly from {city} to {next_city}.")
            
        current_day = end_day
        
    return "\n".join(lines)
