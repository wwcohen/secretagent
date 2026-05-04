"""Auto-generated code-distilled implementation for build_meeting_plan."""

import json
import re
from datetime import datetime, timedelta

def build_meeting_plan(problem_text, json_str, solution_str):
    try:
        data = json.loads(json_str)
        
        # Parse solution order
        # Extract the list from solution_str - it may contain extra text
        match = re.search(r'\[([^\]]*)\]', solution_str)
        if not match:
            return None
        
        names_raw = match.group(1)
        friend_order = [s.strip().strip('"').strip("'") for s in names_raw.split(',') if s.strip()]
        
        my_location = data['my_location']
        my_start_time = data['my_start_time']
        friends_data = {f['name']: f for f in data['friends']}
        travel_times = data['travel_times']
        
        def parse_time(t_str):
            t_str = t_str.strip()
            return datetime.strptime(t_str, "%I:%M %p")
        
        def format_time(dt):
            # Format as H:MM AM/PM (no leading zero on hour)
            hour = dt.hour
            minute = dt.minute
            if hour == 0:
                return f"12:{minute:02d} AM"
            elif hour < 12:
                return f"{hour}:{minute:02d} AM"
            elif hour == 12:
                return f"12:{minute:02d} PM"
            else:
                return f"{hour-12}:{minute:02d} PM"
        
        current_time = parse_time(my_start_time)
        current_location = my_location
        
        steps = []
        steps.append(f"You start at {my_location} at {format_time(current_time)}.")
        
        for friend_name in friend_order:
            if friend_name not in friends_data:
                return None
            
            friend = friends_data[friend_name]
            friend_location = friend['location']
            available_from = parse_time(friend['available_from'])
            available_to = parse_time(friend['available_to'])
            duration_minutes = friend['duration_minutes']
            
            # Travel
            travel_key = f"{current_location}->{friend_location}"
            if travel_key not in travel_times:
                return None
            travel_min = travel_times[travel_key]
            
            steps.append(f"You travel to {friend_location}. It takes {travel_min} minutes.")
            
            current_time += timedelta(minutes=travel_min)
            steps.append(f"You arrive at {format_time(current_time)}.")
            
            # Wait if needed
            if current_time < available_from:
                steps.append(f"You wait until {format_time(available_from)}.")
                current_time = available_from
            
            # Meet
            meet_start = current_time
            meet_end = meet_start + timedelta(minutes=duration_minutes)
            
            # Clamp to availability window
            if meet_end > available_to:
                meet_end = available_to
            
            actual_duration = int((meet_end - meet_start).total_seconds() // 60)
            
            steps.append(f"You meet {friend_name} for {actual_duration} minutes from {format_time(meet_start)} to {format_time(meet_end)}.")
            
            current_time = meet_end
            current_location = friend_location
        
        return "SOLUTION: " + " ".join(steps)
    
    except Exception:
        return None
