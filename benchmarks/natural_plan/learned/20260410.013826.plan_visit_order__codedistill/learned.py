"""Auto-generated code-distilled implementation for plan_visit_order."""

import json
from datetime import datetime, timedelta
from itertools import permutations

def plan_visit_order(text_description, json_data):
    """
    Plan the optimal visit order to meet as many friends as possible.
    
    Args:
        text_description: Text description of the problem
        json_data: JSON string with meeting info
    
    Returns:
        String starting with 'SOLUTION: ' followed by list of friend names
    """
    try:
        data = json.loads(json_data)
    except:
        return None
    
    my_location = data.get("my_location")
    my_start_time = data.get("my_start_time")
    friends = data.get("friends", [])
    travel_times = data.get("travel_times", {})
    
    if not friends:
        return "SOLUTION: []"
    
    # Parse start time
    try:
        start_time = datetime.strptime(my_start_time, "%I:%M %p")
    except:
        return None
    
    # Create a mapping of friend locations
    friend_map = {f["name"]: f for f in friends}
    
    # Try to find the best solution using backtracking
    best_solution = []
    
    def get_travel_time(from_loc, to_loc):
        """Get travel time between two locations"""
        key = f"{from_loc}->{to_loc}"
        return travel_times.get(key, float('inf'))
    
    def time_to_minutes(time_str):
        """Convert time string to minutes since midnight"""
        try:
            t = datetime.strptime(time_str, "%I:%M %p")
            return t.hour * 60 + t.minute
        except:
            return 0
    
    def minutes_to_time(minutes):
        """Convert minutes since midnight to time object"""
        hours = minutes // 60
        mins = minutes % 60
        return datetime.strptime(f"{hours:02d}:{mins:02d}", "%H:%M")
    
    def can_meet_friend(friend_name, current_location, current_time_minutes):
        """Check if we can meet a friend and return end time if possible"""
        friend = friend_map[friend_name]
        travel_time = get_travel_time(current_location, friend["location"])
        
        if travel_time == float('inf'):
            return None
        
        arrival_time = current_time_minutes + travel_time
        avail_start = time_to_minutes(friend["available_from"])
        avail_end = time_to_minutes(friend["available_to"])
        duration_needed = friend["duration_minutes"]
        
        # Check if we can arrive and meet the duration requirement
        meet_start = max(arrival_time, avail_start)
        meet_end = meet_start + duration_needed
        
        if meet_end <= avail_end:
            return meet_end
        
        return None
    
    def backtrack(visited, current_location, current_time_minutes):
        """Backtracking to find best solution"""
        nonlocal best_solution
        
        # Update best solution if current is better
        if len(visited) > len(best_solution):
            best_solution = visited[:]
        
        # Try to visit each unvisited friend
        unvisited = [f["name"] for f in friends if f["name"] not in visited]
        
        # Sort unvisited by earliest availability to improve pruning
        unvisited.sort(key=lambda name: time_to_minutes(friend_map[name]["available_from"]))
        
        for friend_name in unvisited:
            end_time = can_meet_friend(friend_name, current_location, current_time_minutes)
            
            if end_time is not None:
                friend = friend_map[friend_name]
                visited.append(friend_name)
                backtrack(visited, friend["location"], end_time)
                visited.pop()
    
    # Start backtracking from initial location and time
    backtrack([], my_location, time_to_minutes(my_start_time))
    
    return f'SOLUTION: {json.dumps(best_solution)}'
