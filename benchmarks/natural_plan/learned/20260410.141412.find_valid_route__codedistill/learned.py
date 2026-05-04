"""Auto-generated code-distilled implementation for find_valid_route."""

import json
from itertools import permutations

def find_valid_route(text, constraints_str):
    try:
        constraints = json.loads(constraints_str)
    except:
        return '[]'
    
    total_days = constraints['total_days']
    cities = constraints['cities']
    flights = constraints.get('flights', {})
    time_windows = constraints.get('time_windows', [])
    
    city_names = list(cities.keys())
    n = len(city_names)
    
    # Check sum of stays equals total_days
    if sum(cities.values()) != total_days:
        return '[]'
    
    # Build time window lookup
    tw = {}
    for w in time_windows:
        tw[w['city']] = (w['earliest_day'], w['latest_day'])
    
    # Check if flight exists between two cities
    def has_flight(a, b):
        return b in flights.get(a, [])
    
    # For a given ordering, check if it's valid
    def check_order(order):
        # Check consecutive flights
        for i in range(len(order) - 1):
            if not has_flight(order[i], order[i+1]):
                return False
        
        # Check time windows
        day = 1
        for city in order:
            stay = cities[city]
            start_day = day
            end_day = day + stay - 1
            if city in tw:
                earliest, latest = tw[city]
                if start_day < earliest or end_day > latest:
                    return False
            day = end_day + 1
        
        return True
    
    # For small n, try permutations
    if n <= 10:
        # Use backtracking with pruning for efficiency
        result = []
        used = [False] * n
        
        def backtrack(path, current_day):
            if len(path) == n:
                result.append(path[:])
                return True
            
            for i in range(n):
                if used[i]:
                    continue
                city = city_names[i]
                stay = cities[city]
                start_day = current_day
                end_day = current_day + stay - 1
                
                # Check flight from previous city
                if path and not has_flight(path[-1], city):
                    continue
                
                # Check time window
                if city in tw:
                    earliest, latest = tw[city]
                    if start_day < earliest or end_day > latest:
                        continue
                
                # Check if remaining days can fit
                remaining_days = sum(cities[city_names[j]] for j in range(n) if not used[j] and j != i)
                if end_day + remaining_days != total_days:
                    # remaining cities must fill exactly the rest
                    pass  # still try, the check is end_day + remaining == total_days
                
                if end_day + remaining_days != total_days:
                    continue
                
                # Pruning: check if any remaining city with time window can still fit
                feasible = True
                future_day = end_day + 1
                # Quick check: any constrained city that hasn't been placed
                for j in range(n):
                    if not used[j] and j != i and city_names[j] in tw:
                        cj = city_names[j]
                        ej, lj = tw[cj]
                        sj = cities[cj]
                        # earliest it could start is future_day, latest end is total_days
                        if future_day > lj or ej > total_days - sj + 1:
                            pass  # can't determine order, skip deep check
                
                used[i] = True
                path.append(city)
                if backtrack(path, end_day + 1):
                    return True
                path.pop()
                used[i] = False
            
            return False
        
        if backtrack([], 1):
            return json.dumps(result[0])
        else:
            return '[]'
    
    return '[]'
