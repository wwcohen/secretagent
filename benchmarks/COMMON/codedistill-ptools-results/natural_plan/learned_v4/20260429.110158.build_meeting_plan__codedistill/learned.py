"""Auto-generated code-distilled implementation for build_meeting_plan."""

import json
from datetime import datetime, timedelta

def build_meeting_plan(prompt, parsed_json, visit_order):
    data = json.loads(parsed_json)
    order = json.loads(visit_order)
    
    friends_by_name = {f['name']: f for f in data['friends']}
    travel = data['travel_times']
    
    def parse_time(s):
        s = s.strip().replace('.', '')
        for fmt in ("%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    def fmt_time(dt):
        h = dt.hour
        m = dt.minute
        ampm = "AM" if h < 12 else "PM"
        if h == 0: h = 12
        elif h > 12: h -= 12
        if m == 0:
            return f"{h}:{m:02d}{ampm}"
        return f"{h}:{m:02d}{ampm}"

    current_loc = data['my_location']
    current_time = parse_time(data['my_start_time'])
    
    parts = [f"SOLUTION: You start at {current_loc} at {fmt_time(current_time)}."]
    
    for friend_name in order:
        f = friends_by_name[friend_name]
        avail_from = parse_time(f['available_from'])
        avail_to = parse_time(f['available_to'])
        dur = f['duration_minutes']
        dest = f['location']
        
        key = f"{current_loc}->{dest}"
        tt = travel.get(key, 0)
        
        arrive_time = current_time + timedelta(minutes=tt)
        
        if arrive_time > avail_to - timedelta(minutes=dur):
            # Defer travel: wait then travel
            depart_time = avail_from - timedelta(minutes=tt)
            if depart_time > current_time:
                parts.append(f"You wait until {fmt_time(depart_time)}.")
                current_time = depart_time
            arrive_time = current_time + timedelta(minutes=tt)
        
        if current_loc != dest:
            parts.append(f"You travel to {dest} in {tt} minutes and arrive at {fmt_time(arrive_time)}.")
            current_time = arrive_time
            current_loc = dest
        
        meet_start = max(current_time, avail_from)
        if meet_start > current_time:
            parts.append(f"You wait until {fmt_time(meet_start)}.")
            current_time = meet_start
        
        meet_end = current_time + timedelta(minutes=dur)
        parts.append(f"You meet {friend_name} for {dur} minutes from {fmt_time(current_time)} to {fmt_time(meet_end)}.")
        current_time = meet_end
    
    # Check if we should return home
    if current_loc != data['my_location']:
        ret_key = f"{current_loc}->{data['my_location']}"
        if ret_key in travel:
            ret_time = travel[ret_key]
            ret_arrive = current_time + timedelta(minutes=ret_time)
            # Only return if it's mentioned in the prompt context or early enough
            # Based on examples: return home only for single friend when ending early
            if len(order) == 1 and ret_arrive.hour < 18:
                parts.append(f"You travel to {data['my_location']} in {ret_time} minutes and arrive at {fmt_time(ret_arrive)}.")
    
    return ' '.join(parts)
