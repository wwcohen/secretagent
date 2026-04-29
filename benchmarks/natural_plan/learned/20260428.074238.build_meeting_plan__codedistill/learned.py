"""Auto-generated code-distilled implementation for build_meeting_plan."""

import json
import re
from datetime import datetime, timedelta

def build_meeting_plan(problem_text, json_data_str, order_str):
    try:
        # Clean up json_data_str - it might have "SOLUTION:" prefix or other text
        json_str = json_data_str.strip()
        if json_str.upper().startswith("SOLUTION:"):
            json_str = json_str[len("SOLUTION:"):].strip()
        
        data = json.loads(json_str)
        
        # Clean up order_str
        order_clean = order_str.strip()
        if order_clean.upper().startswith("SOLUTION:"):
            order_clean = order_clean[len("SOLUTION:"):].strip()
        
        order = json.loads(order_clean)
        
        my_location = data["my_location"]
        my_start_time = data["my_start_time"]
        friends = {f["name"]: f for f in data["friends"]}
        travel_times = data["travel_times"]
        
        def parse_time(t_str):
            t_str = t_str.strip().upper().replace(" ", "")
            # Handle formats like "9:00AM", "5:15PM", "12:00PM"
            for fmt in ["%I:%M%p", "%I:%M %p"]:
                try:
                    return datetime.strptime(t_str, fmt)
                except ValueError:
                    continue
            return None
        
        def format_time(dt):
            # Format as "9:00AM", "12:15PM", etc.
            hour = dt.hour
            minute = dt.minute
            if hour == 0:
                return f"12:{minute:02d}AM"
            elif hour < 12:
                return f"{hour}:{minute:02d}AM"
            elif hour == 12:
                return f"12:{minute:02d}PM"
            else:
                return f"{hour-12}:{minute:02d}PM"
        
        def get_travel_time(from_loc, to_loc):
            # Try different key formats
            for sep in ["->", " to "]:
                key = f"{from_loc}{sep}{to_loc}"
                if key in travel_times:
                    return travel_times[key]
            return None
        
        current_time = parse_time(my_start_time)
        current_location = my_location
        
        parts = [f"SOLUTION: You start at {my_location} at {format_time(current_time)}."]
        
        for friend_name in order:
            friend = friends[friend_name]
            friend_location = friend["location"]
            available_from = parse_time(friend["available_from"])
            duration = friend["duration_minutes"]
            
            # Travel to friend's location
            if current_location != friend_location:
                tt = get_travel_time(current_location, friend_location)
                arrive_time = current_time + timedelta(minutes=tt)
                parts.append(f"You travel to {friend_location} in {tt} minutes and arrive at {format_time(arrive_time)}.")
                current_time = arrive_time
                current_location = friend_location
            
            # Wait if needed
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
