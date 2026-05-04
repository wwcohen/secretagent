"""Auto-generated code-distilled implementation for find_valid_route."""

import json
from itertools import permutations

def find_valid_route(problem_text, constraints_json):
    try:
        constraints = json.loads(constraints_json)
    except (json.JSONDecodeError, TypeError):
        return None
    
    total_days = constraints.get("total_days")
    cities = constraints.get("cities", {})
    flights = constraints.get("flights", {})
    time_windows = constraints.get("time_windows", [])
    
    if not cities:
        return None
    
    city_names = list(cities.keys())
    durations = cities
    
    # Build time window lookup
    tw_lookup = {}
    for tw in time_windows:
        tw_lookup[tw["city"]] = (tw["earliest_day"], tw["latest_day"])
    
    # Check if two cities have a direct flight
    def has_flight(a, b):
        return b in flights.get(a, [])
    
    # Try all permutations and find a valid one
    def check_route(route):
        # Check flight connections between consecutive cities
        for i in range(len(route) - 1):
            if not has_flight(route[i], route[i+1]):
                return False
        
        # Check time windows
        current_day = 1
        for city in route:
            start_day = current_day
            end_day = current_day + durations[city] - 1
            
            if city in tw_lookup:
                earliest, latest = tw_lookup[city]
                # The visit must overlap with or fit within the time window
                # Based on examples: start_day >= earliest and end_day <= latest
                if start_day < earliest or end_day > latest:
                    return False
            
            current_day = end_day + 1
        
        # Check total days
        if current_day - 1 != total_days:
            return False
        
        return True
    
    # For efficiency, try DFS with pruning for larger instances
    def dfs(route, visited, current_day):
        if len(route) == len(city_names):
            if current_day - 1 == total_days:
                return list(route)
            return None
        
        last_city = route[-1] if route else None
        
        for city in city_names:
            if city in visited:
                continue
            if last_city and not has_flight(last_city, city):
                continue
            
            start_day = current_day
            end_day = current_day + durations[city] - 1
            
            if city in tw_lookup:
                earliest, latest = tw_lookup[city]
                if start_day < earliest or end_day > latest:
                    continue
            
            visited.add(city)
            route.append(city)
            result = dfs(route, visited, end_day + 1)
            if result is not None:
                return result
            route.pop()
            visited.remove(city)
        
        return None
    
    result = dfs([], set(), 1)
    
    if result is None:
        return None
    
    return json.dumps(result)
