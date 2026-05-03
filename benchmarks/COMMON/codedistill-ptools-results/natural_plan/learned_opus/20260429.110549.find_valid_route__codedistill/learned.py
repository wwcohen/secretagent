"""Auto-generated code-distilled implementation for find_valid_route."""

import json
import re
from itertools import permutations

def find_valid_route(prompt, constraints_json):
    try:
        # Clean up constraints_json - sometimes it has extra text
        # Find the first valid JSON object
        brace_count = 0
        start = None
        end = None
        for i, c in enumerate(constraints_json):
            if c == '{':
                if start is None:
                    start = i
                brace_count += 1
            elif c == '}':
                brace_count -= 1
                if brace_count == 0 and start is not None:
                    end = i + 1
                    break
        
        if start is not None and end is not None:
            json_str = constraints_json[start:end]
        else:
            json_str = constraints_json
        
        constraints = json.loads(json_str)
        
        total_days = constraints["total_days"]
        cities = constraints["cities"]  # dict: city -> days
        flights = constraints["flights"]  # dict: city -> [connected cities]
        time_windows = constraints.get("time_windows", [])
        
        city_names = list(cities.keys())
        n = len(city_names)
        
        # Build adjacency check
        def has_flight(a, b):
            return b in flights.get(a, []) or a in flights.get(b, [])
        
        # Try all permutations
        for perm in permutations(city_names):
            # Check flight connectivity
            valid_flights = True
            for i in range(len(perm) - 1):
                if not has_flight(perm[i], perm[i+1]):
                    valid_flights = False
                    break
            if not valid_flights:
                continue
            
            # Calculate day ranges for each city in this permutation
            # Day 1 is the first day. Each city's stay overlaps by 1 day with the next (shared flight day)
            # City i starts at: 1 + sum(cities[perm[j]] for j<i) - i (because i shared days)
            # City i ends at: start + cities[perm[i]] - 1
            
            day_pos = {}
            current_day = 1
            for i, city in enumerate(perm):
                start_day = current_day
                end_day = start_day + cities[city] - 1
                day_pos[city] = (start_day, end_day)
                # Next city starts on end_day (shared flight day)
                current_day = end_day  # shared day: next city starts on this day
            
            # Check total days
            last_city = perm[-1]
            if day_pos[last_city][1] != total_days:
                continue
            
            # Check time windows
            valid_windows = True
            for tw in time_windows:
                city = tw["city"]
                earliest = tw["earliest_day"]
                latest = tw["latest_day"]
                city_start, city_end = day_pos[city]
                if city_start < earliest or city_end > latest:
                    valid_windows = False
                    break
            
            if valid_windows:
                return json.dumps(list(perm))
        
        return None
    except Exception:
        return None
