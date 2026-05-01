"""Auto-generated code-distilled implementation for find_valid_route."""

import json
import re

def find_valid_route(problem_text, constraints_json):
    """
    Finds a valid trip route based on the given problem text and constraints.
    
    Args:
        problem_text (str): The natural language description of the problem.
        constraints_json (str): A string containing the JSON constraints.
        
    Returns:
        str: A JSON-formatted string representing the list of cities in the valid route,
             or None if no valid route could be confidently found.
    """
    # Extract the JSON object from the constraints_json string
    match = re.search(r'(\{.*\})', constraints_json, re.DOTALL)
    if not match:
        return None
    
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
        
    cities_dict = data.get("cities", {})
    flights = data.get("flights", {})
    time_windows = data.get("time_windows", [])
    
    # Preprocess time windows into a dictionary for quick lookup
    tw_dict = {}
    for tw in time_windows:
        city = tw.get("city")
        if not city:
            continue
        if city not in tw_dict:
            tw_dict[city] = []
        tw_dict[city].append({
            "earliest": int(tw["earliest_day"]),
            "latest": int(tw["latest_day"])
        })
        
    all_cities = list(cities_dict.keys())
    n = len(all_cities)
    
    if n == 0:
        return "[]"
        
    def dfs(current_route, current_day):
        # Base case: all cities have been visited
        if len(current_route) == n:
            return list(current_route)
            
        last_city = current_route[-1] if current_route else None
        
        # Determine the next candidate cities to visit
        if last_city is None:
            candidates = all_cities
        else:
            candidates = flights.get(last_city, [])
            
        for city in candidates:
            if city in current_route or city not in cities_dict:
                continue
                
            stay = cities_dict[city]
            start_day = current_day
            end_day = current_day + stay - 1
            
            # Check time window constraints for the target city
            valid = True
            if city in tw_dict:
                for tw in tw_dict[city]:
                    if start_day < tw["earliest"] or end_day > tw["latest"]:
                        valid = False
                        break
            if not valid:
                continue
                
            # Recurse: next city's start_day will be exactly the end_day of the current city
            # (since flight days are shared/overlap with the departure/arrival days)
            current_route.append(city)
            res = dfs(current_route, end_day)
            if res is not None:
                return res
            current_route.pop()
            
        return None
        
    # Execute backtracking search starting at Day 1
    result = dfs([], 1)
    
    if result is not None:
        return json.dumps(result)
        
    return None
