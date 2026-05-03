"""Auto-generated code-distilled implementation for plan_visit_order."""

import json
from itertools import permutations
from datetime import datetime, timedelta

def parse_time(t):
    t = t.strip().upper().replace(".", "")
    for fmt in ("%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    return None

def plan_visit_order(prompt, structured_json):
    try:
        data = json.loads(structured_json)
    except:
        return None
    
    my_location = data["my_location"]
    my_start_time = parse_time(data["my_start_time"])
    friends = data["friends"]
    travel_times = data["travel_times"]
    
    def get_travel_time(src, dst):
        if src == dst:
            return 0
        key = f"{src}->{dst}"
        return travel_times.get(key, None)
    
    def simulate(order):
        """Try to visit friends in given order, return list of successfully visited friends."""
        current_time = my_start_time
        current_loc = my_location
        visited = []
        
        for idx in order:
            f = friends[idx]
            name = f["name"]
            loc = f["location"]
            avail_from = parse_time(f["available_from"])
            avail_to = parse_time(f["available_to"])
            duration = f["duration_minutes"]
            
            tt = get_travel_time(current_loc, loc)
            if tt is None:
                continue
            
            arrive_time = current_time + timedelta(minutes=tt)
            
            # Meeting starts at max(arrive_time, avail_from)
            meeting_start = max(arrive_time, avail_from)
            
            # Meeting ends
            meeting_end = meeting_start + timedelta(minutes=duration)
            
            # Check if meeting fits within availability
            if meeting_end <= avail_to:
                visited.append(idx)
                current_time = meeting_end
                current_loc = loc
        
        return visited
    
    n = len(friends)
    
    if n == 0:
        return json.dumps([])
    
    best_visited = []
    best_count = 0
    
    # For small n, try all permutations
    # For larger n, we still need to try permutations but can prune
    if n <= 10:
        indices = list(range(n))
        for perm in permutations(indices):
            visited = simulate(perm)
            if len(visited) > best_count:
                best_count = len(visited)
                best_visited = visited
                if best_count == n:
                    break
        
        result = [friends[i]["name"] for i in best_visited]
        return json.dumps(result)
    else:
        # For very large n, use greedy approach with multiple strategies
        # Try all permutations of subsets - but this is impractical
        # Use greedy by earliest available_from
        indices = list(range(n))
        
        # Try multiple sorting strategies
        strategies = [
            sorted(indices, key=lambda i: parse_time(friends[i]["available_from"])),
            sorted(indices, key=lambda i: parse_time(friends[i]["available_to"])),
            sorted(indices, key=lambda i: parse_time(friends[i]["available_to"]) - timedelta(minutes=friends[i]["duration_minutes"])),
        ]
        
        for strat in strategies:
            visited = simulate(strat)
            if len(visited) > best_count:
                best_count = len(visited)
                best_visited = visited
        
        result = [friends[i]["name"] for i in best_visited]
        return json.dumps(result)
