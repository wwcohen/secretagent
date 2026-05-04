"""Auto-generated code-distilled implementation for build_trip_plan."""

import json
import re

def build_trip_plan(problem_text, constraints_json, route_info):
    try:
        constraints = json.loads(constraints_json)
    except:
        return None
    
    cities_durations = constraints.get("cities", {})
    total_days = constraints.get("total_days", 0)
    num_cities = len(cities_durations)
    
    # Try to extract route from route_info
    route = None
    
    # First, try to parse as a JSON list
    try:
        parsed = json.loads(route_info.strip())
        if isinstance(parsed, list):
            route = parsed
    except:
        pass
    
    # If not a simple JSON list, try to extract route from the reasoning text
    if route is None:
        # Look for pattern like "the route: City1, City2, City3, City4, City5"
        # or "So the route: X, Y, Z, W, V."
        # Also look for "Route: ..." or ordered city sequences
        
        # Try multiple patterns to find the route
        patterns = [
            r'(?:the |final |valid |So the |our )route[:\s]+([A-Z][a-zéèêë]+(?:[\s,->]+[A-Z][a-zéèêë]+){' + str(num_cities-1) + r'})',
            r'route[:\s]*\[([^\]]+)\]',
            r'(?:Reykjavik|Stuttgart|Split|Santorini|Zurich|Istanbul|Vilnius|Hamburg|Florence|Warsaw|Munich|Frankfurt|Krakow|Salzburg)(?:\s*[->,→]+\s*(?:Reykjavik|Stuttgart|Split|Santorini|Zurich|Istanbul|Vilnius|Hamburg|Florence|Warsaw|Munich|Frankfurt|Krakow|Salzburg)){' + str(num_cities-1) + r'}',
        ]
        
        city_names = list(cities_durations.keys())
        city_pattern = '|'.join(re.escape(c) for c in city_names)
        
        # Find sequences of all cities connected by arrows, commas, or "then"
        arrow_pattern = r'(?:' + city_pattern + r')(?:\s*(?:->|→|,)\s*(?:' + city_pattern + r')){' + str(num_cities - 1) + r'}'
        matches = re.findall(arrow_pattern, route_info)
        if matches:
            last_match = matches[-1]
            route = re.findall(city_pattern, last_match)
        
        if route is None or len(route) != num_cities:
            # Try finding "route: CityA, CityB, CityC..." pattern
            route_match = re.search(r'(?:route|order)[:\s]+(' + city_pattern + r')(?:\s*[,→\->]+\s*(' + city_pattern + r'))+', route_info, re.IGNORECASE)
            if route_match:
                segment = route_match.group(0)
                route = re.findall(city_pattern, segment)
            
        if route is None or len(route) != num_cities:
            # Find the last occurrence of all city names in sequence
            all_sequences = re.findall(r'(?:' + city_pattern + r')(?:[,\s\->→and]+(?:' + city_pattern + r')){' + str(num_cities-1) + r'}', route_info)
            if all_sequences:
                route = re.findall(city_pattern, all_sequences[-1])
    
    if route is None or len(route) != num_cities:
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
            current_day = end_day  # shared day
    
    return '\n'.join(lines)
