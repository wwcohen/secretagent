"""Auto-generated code-distilled implementation for build_meeting_plan."""

import json
import re
from datetime import datetime, timedelta

def build_meeting_plan(prompt, parsed_info_json, visit_order_json):
    try:
        # Parse the JSON inputs - handle potential "SOLUTION:\n" prefix
        parsed_str = parsed_info_json.strip()
        if parsed_str.upper().startswith("SOLUTION:"):
            parsed_str = parsed_str[len("SOLUTION:"):].strip()
        
        info = json.loads(parsed_str)
        order = json.loads(visit_order_json)
        
        my_location = info["my_location"]
        my_start_time = info["my_start_time"]
        friends = {f["name"]: f for f in info["friends"]}
        travel_times = info["travel_times"]
        
        def parse_time(t_str):
            t_str = t_str.strip().upper().replace(" ", "")
            # Handle formats like "9:00AM", "9:00 AM", "5:00PM"
            for fmt in ["%I:%M%p", "%I:%M %p"]:
                try:
                    return datetime.strptime(t_str, fmt)
                except ValueError:
                    continue
            return None
        
        def format_time(dt):
            h = dt.strftime("%I").lstrip("0")
            m = dt.strftime(":%M")
            ap = dt.strftime("%p").upper()
            return f"{h}{m}{ap}"
        
        def get_travel_time(from_loc, to_loc):
            # Try different key formats
            for key in [f"{from_loc}->{to_loc}", f"{from_loc} to {to_loc}",
                        f"{from_loc}>{to_loc}", f"{from_loc} -> {to_loc}"]:
                if key in travel_times:
                    return travel_times[key]
            # Try with arrow variants
            for key, val in travel_times.items():
                # Normalize the key
                normalized = key.replace("->", " to ").replace(" to ", " to ")
                check = f"{from_loc} to {to_loc}"
                if normalized.strip().lower() == check.strip().lower():
                    return val
            return None
        
        current_time = parse_time(my_start_time)
        current_location = my_location
        
        parts = [f"SOLUTION: You start at {my_location} at {format_time(current_time)}."]
        
        for friend_name in order:
            friend = friends[friend_name]
            friend_location = friend["location"]
            available_from = parse_time(friend["available_from"])
            available_to = parse_time(friend["available_to"])
            duration = friend["duration_minutes"]
            
            # Travel to friend's location if not already there
            if current_location != friend_location:
                tt = get_travel_time(current_location, friend_location)
                if tt is None:
                    return None
                arrival_time = current_time + timedelta(minutes=tt)
                parts.append(f"You travel to {friend_location} in {tt} minutes and arrive at {format_time(arrival_time)}.")
                current_time = arrival_time
                current_location = friend_location
            
            # Wait if friend is not available yet
            if current_time < available_from:
                parts.append(f"You wait until {format_time(available_from)}.")
                current_time = available_from
            
            # Meet the friend
            meet_start = current_time
            meet_end = meet_start + timedelta(minutes=duration)
            parts.append(f"You meet {friend_name} for {duration} minutes from {format_time(meet_start)} to {format_time(meet_end)}.")
            current_time = meet_end
        
        return " ".join(parts)
    
    except Exception:
        return None
