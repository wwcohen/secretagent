"""Auto-generated code-distilled implementation for find_valid_route."""

import json
from itertools import permutations

def find_valid_route(text, constraints_str):
    constraints = json.loads(constraints_str)
    total_days = constraints["total_days"]
    cities = constraints["cities"]
    flights = constraints["flights"]
    time_windows = constraints["time_windows"]
    
    city_names = list(cities.keys())
    n = len(city_names)
    
    # Check if sum of stays equals total_days
    if sum(cities.values()) != total_days:
        return json.dumps([])
    
    # Build time window lookup
    tw = {}
    for w in time_windows:
        tw[w["city"]] = (w["earliest_day"], w["latest_day"])
    
    # Check adjacency
    def has_flight(a, b):
        return b in flights.get(a, [])
    
    # For each city, compute valid start day range
    # City at position i in route: start_day = sum of durations of cities before it + 1
    # We need: for cities with time windows, earliest <= start <= latest - duration + 1
    
    def check_route(route):
        # Check flights between consecutive cities
        for i in range(len(route) - 1):
            if not has_flight(route[i], route[i+1]):
                return False
        
        # Check time windows
        day = 1
        for city in route:
            duration = cities[city]
            start = day
            end = day + duration - 1
            if city in tw:
                earliest, latest = tw[city]
                if start < earliest or end > latest:
                    return False
            day = end + 1
        
        return True
    
    # For small n, try permutations; for larger n, use backtracking with pruning
    if n <= 8:
        for perm in permutations(city_names):
            if check_route(list(perm)):
                return json.dumps(list(perm))
        return json.dumps([])
    
    # Backtracking with pruning for larger instances
    result = []
    
    def backtrack(route, used, current_day):
        if len(route) == n:
            result.append(list(route))
            return True
        
        for city in city_names:
            if city in used:
                continue
            
            # Check flight from last city
            if route and not has_flight(route[-1], city):
                continue
            
            duration = cities[city]
            start = current_day
            end = current_day + duration - 1
            
            # Check time window
            if city in tw:
                earliest, latest = tw[city]
                if start < earliest or end > latest:
                    continue
            
            # Check if remaining cities can still fit
            remaining_days = total_days - (end)
            remaining_cities = [c for c in city_names if c not in used and c != city]
            remaining_stay = sum(cities[c] for c in remaining_cities)
            if remaining_stay != remaining_days:
                continue
            
            # Check if any remaining city with time window can still be satisfied
            future_day = end + 1
            feasible = True
            for rc in remaining_cities:
                if rc in tw:
                    e, l = tw[rc]
                    rd = cities[rc]
                    # The earliest this city could start is future_day, latest is total_days - rd + 1
                    max_possible_start = total_days - rd + 1
                    if max_possible_start < e or future_day > l - rd + 1:
                        # Could still work if not placed first among remaining
                        pass
            
            used.add(city)
            route.append(city)
            if backtrack(route, used, end + 1):
                return True
            route.pop()
            used.remove(city)
        
        return False
    
    backtrack([], set(), 1)
    
    if result:
        return json.dumps(result[0])
    return json.dumps([])
