"""Auto-generated code-distilled implementation for plan_visit_order."""

import json
import re
from itertools import permutations
from datetime import datetime, timedelta

def plan_visit_order(prompt, solution_json):
    try:
        # Strip "SOLUTION:" prefix if present
        cleaned = solution_json.strip()
        if cleaned.upper().startswith("SOLUTION:"):
            cleaned = cleaned[len("SOLUTION:"):].strip()
        
        data = json.loads(cleaned)
    except:
        return None
    
    my_location = data["my_location"]
    my_start_time = parse_time(data["my_start_time"])
    friends = data["friends"]
    travel_times = {}
    
    for key, val in data["travel_times"].items():
        # Handle both "->" and " to " separators
        if "->" in key:
            parts = key.split("->")
        else:
            parts = key.split(" to ")
        if len(parts) == 2:
            travel_times[(parts[0].strip(), parts[1].strip())] = val
    
    n = len(friends)
    
    best_order = None
    best_count = -1
    best_end_time = None
    
    for perm in permutations(range(n)):
        count, end_time, order = simulate(perm, friends, my_location, my_start_time, travel_times)
        if count > best_count or (count == best_count and end_time is not None and (best_end_time is None or end_time < best_end_time)):
            best_count = count
            best_end_time = end_time
            best_order = order
    
    if best_order is None or best_count == 0:
        if best_count == 0:
            return '[]'
        return None
    
    return json.dumps(best_order)

def parse_time(t_str):
    t_str = t_str.strip().upper().replace(" ", "")
    # Handle formats like "9:00AM", "9:00 AM"
    for fmt in ["%I:%M%p", "%I:%M %p"]:
        try:
            return datetime.strptime(t_str, fmt)
        except:
            continue
    return None

def simulate(perm, friends, my_location, start_time, travel_times):
    current_location = my_location
    current_time = start_time
    visited = []
    
    for idx in perm:
        f = friends[idx]
        name = f["name"]
        loc = f["location"]
        avail_from = parse_time(f["available_from"])
        avail_to = parse_time(f["available_to"])
        duration = f["duration_minutes"]
        
        # Travel to friend's location
        tt = travel_times.get((current_location, loc), None)
        if tt is None:
            if current_location == loc:
                tt = 0
            else:
                continue  # Can't reach, skip this friend
        
        arrive_time = current_time + timedelta(minutes=tt)
        
        # Wait until friend is available
        meet_start = max(arrive_time, avail_from)
        
        # Check if we can meet for the required duration within their availability
        meet_end = meet_start + timedelta(minutes=duration)
        
        if meet_end > avail_to:
            continue  # Can't meet this friend, skip
        
        # Successfully meet this friend
        visited.append(name)
        current_time = meet_end
        current_location = loc
    
    return len(visited), current_time, visited
