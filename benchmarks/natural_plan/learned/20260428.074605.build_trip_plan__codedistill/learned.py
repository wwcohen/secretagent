"""Auto-generated code-distilled implementation for build_trip_plan."""

import json
import re

def build_trip_plan(problem_text, constraints_json, route_str):
    constraints = json.loads(constraints_json)
    cities_durations = constraints["cities"]
    total_days = constraints["total_days"]
    num_cities = len(cities_durations)
    
    # Try to parse route as JSON array first
    route = None
    try:
        parsed = json.loads(route_str)
        if isinstance(parsed, list):
            route = parsed
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If not a JSON array, extract route from reasoning text
    if route is None:
        city_names = list(cities_durations.keys())
        
        # Look for patterns like "So the route: City1, City2, City3, City4, City5."
        # or "the route should be: ..."
        # Try multiple patterns
        patterns = [
            r'(?:So |So, |Therefore, )?[Tt]he route[^:]*:\s*([A-Z][^.\n]+)',
            r'route[^:]*:\s*([A-Z][^\n.]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, route_str)
            for match in matches:
                # Split by comma or " -> "
                parts = re.split(r'\s*(?:,|->)\s*', match.strip().rstrip('.'))
                parts = [p.strip() for p in parts if p.strip()]
                if len(parts) == num_cities and all(p in cities_durations for p in parts):
                    route = parts
                    break
            if route:
                break
        
        # If still no route, try to find the valid permutation from the reasoning
        if route is None:
            # Look for "Reykjavik, Stuttgart, Split, Zurich, Santorini" pattern with all cities
            city_pattern = '|'.join(re.escape(c) for c in city_names)
            all_sequences = re.findall(r'(?:' + city_pattern + r')(?:\s*(?:,|->|then(?:\s+fly)?\s+to)\s*(?:' + city_pattern + r'))+', route_str)
            for seq in reversed(all_sequences):  # prefer later mentions
                parts = re.split(r'\s*(?:,|->|then(?:\s+fly)?\s+to)\s*', seq.strip().rstrip('.'))
                parts = [p.strip() for p in parts if p.strip()]
                if len(parts) == num_cities and all(p in cities_durations for p in parts):
                    route = parts
                    break
    
    if route is None:
        return None
    
    # Build the trip plan
    lines = []
    lines.append(f"Here is the trip plan for visiting the {num_cities} European cities for {total_days} days:")
    
    current_day = 1
    for i, city in enumerate(route):
        duration = cities_durations[city]
        end_day = current_day + duration - 1
        
        lines.append(f"**Day {current_day}-{end_day}:** Visit {city} for {duration} days.")
        
        if i < len(route) - 1:
            next_city = route[i + 1]
            lines.append(f"**Day {end_day}:** Fly from {city} to {next_city}.")
            current_day = end_day  # flight day is shared
    
    return '\n'.join(lines)
