"""Auto-generated code-distilled implementation for plan_visit_order."""

import json
import re
from itertools import permutations
from datetime import datetime, timedelta

def plan_visit_order(prompt, data_str):
    # Detect if output should have SOLUTION: prefix
    prefix = ""
    if "SOLUTION:" in data_str.split("{")[0] if "{" in data_str else data_str:
        prefix = "SOLUTION:\n"
    
    # Clean the data string
    clean = data_str.strip()
    if clean.startswith("SOLUTION:"):
        clean = clean[len("SOLUTION:"):].strip()
    
    try:
        data = json.loads(clean)
    except:
        return None
    
    my_location = data["my_location"]
    my_start_time = parse_time(data["my_start_time"])
    friends = data["friends"]
    travel_times_raw = data["travel_times"]
    
    # Normalize travel time keys (handle both "->" and " to ")
    travel_times = {}
    for k, v in travel_times_raw.items():
        # Normalize separator to "->"
        normalized = k.replace(" to ", "->") if " to " in k else k
        travel_times[normalized] = v
    
    def get_travel_time(frm, to):
        key = f"{frm}->{to}"
        if key in travel_times:
            return travel_times[key]
        return None
    
    n = len(friends)
    
    best_count = 0
    best_order = []
    best_earliest_end = None
    
    # Try all permutations of all subsets (ordered by size descending)
    for size in range(n, 0, -1):
        if size < best_count:
            break
        from itertools import combinations
        for combo in combinations(range(n), size):
            for perm in permutations(combo):
                result = simulate(perm, friends, my_location, my_start_time, get_travel_time)
                if result is not None:
                    count, end_time, names = result
                    if count > best_count or (count == best_count and (best_earliest_end is None or end_time < best_earliest_end)):
                        best_count = count
                        best_order = names
                        best_earliest_end = end_time
        if best_count == size:
            break
    
    result_json = json.dumps(best_order)
    return prefix + result_json

def parse_time(t_str):
    t_str = t_str.strip().upper().replace(" ", "")
    # Parse time like "9:00AM", "5:15PM"
    for fmt in ["%I:%M%p", "%I:%M %p"]:
        try:
            return datetime.strptime(t_str, fmt)
        except:
            continue
    t_str2 = t_str.replace(" ", "")
    return datetime.strptime(t_str2, "%I:%M%p")

def simulate(perm, friends, my_location, start_time, get_travel_time):
    current_time = start_time
    current_loc = my_location
    names = []
    
    for idx in perm:
        f = friends[idx]
        tt = get_travel_time(current_loc, f["location"])
        if tt is None:
            if current_loc == f["location"]:
                tt = 0
            else:
                return None
        
        arrive_time = current_time + timedelta(minutes=tt)
        avail_from = parse_time(f["available_from"])
        avail_to = parse_time(f["available_to"])
        duration = f["duration_minutes"]
        
        meeting_start = max(arrive_time, avail_from)
        meeting_end = meeting_start + timedelta(minutes=duration)
        
        if meeting_end > avail_to:
            return None
        
        current_time = meeting_end
        current_loc = f["location"]
        names.append(f["name"])
    
    return (len(names), current_time, names)
