"""Auto-generated code-distilled implementation for plan_visit_order."""

import json
import re

def plan_visit_order(prompt, json_str):
    try:
        data = json.loads(json_str)
    except Exception:
        return None
        
    start_loc = data.get("my_location", "").strip()
    start_time_str = data.get("my_start_time", "").strip()
    friends = data.get("friends", [])
    travel_times = data.get("travel_times", {})
    
    if not start_loc or not start_time_str:
        return None
        
    def parse_time(t_str):
        m = re.match(r"(\d+):(\d+)\s*(AM|PM)", t_str.strip(), re.IGNORECASE)
        if not m:
            return 0
        h, m_minute, ampm = m.groups()
        h = int(h)
        m_minute = int(m_minute)
        ampm = ampm.upper()
        if ampm == "PM" and h != 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
        return h * 60 + m_minute

    def get_travel_time(loc1, loc2):
        l1, l2 = loc1.strip(), loc2.strip()
        if l1 == l2:
            return 0
        k1 = f"{l1}->{l2}"
        if k1 in travel_times:
            return travel_times[k1]
        k2 = f"{l1} to {l2}"
        if k2 in travel_times:
            return travel_times[k2]
        for k, v in travel_times.items():
            if "->" in k:
                parts = k.split("->")
            elif " to " in k:
                parts = k.split(" to ")
            else:
                continue
            if len(parts) == 2:
                if parts[0].strip() == l1 and parts[1].strip() == l2:
                    return v
        return 999999
        
    for f in friends:
        f['from_mins'] = parse_time(f['available_from'])
        f['to_mins'] = parse_time(f['available_to'])
        if f['to_mins'] < f['from_mins']:
            f['to_mins'] += 24 * 60
        f['duration'] = int(f['duration_minutes'])
        f['location'] = f['location'].strip()
        
    curr_time = parse_time(start_time_str)
    
    best_path = []
    
    def dfs(curr_loc, current_time, visited, path):
        nonlocal best_path
        # Keep strictly the first path found of the maximum length
        if len(path) > len(best_path):
            best_path = list(path)
            
        for i, f in enumerate(friends):
            if i not in visited:
                tt = get_travel_time(curr_loc, f['location'])
                if tt == 999999:
                    continue
                arr_time = current_time + tt
                start_time = max(arr_time, f['from_mins'])
                end_time = start_time + f['duration']
                if end_time <= f['to_mins']:
                    dfs(f['location'], end_time, visited | {i}, path + [f['name']])
                    
    dfs(start_loc, curr_time, set(), [])
    
    return json.dumps(best_path)
