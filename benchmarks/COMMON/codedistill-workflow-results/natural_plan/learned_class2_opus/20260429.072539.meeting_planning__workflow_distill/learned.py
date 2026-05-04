"""Auto-generated workflow-distilled implementation for meeting_planning.

Calls existing tools from ptools_meeting.
"""

from ptools_meeting import *

import re
from itertools import permutations

def meeting_planning(prompt: str) -> list:
    # Parse the problem
    try:
        # Extract travel distances
        travel_times = {}
        travel_pattern = re.findall(r'([A-Za-z\' ]+?) to ([A-Za-z\' ]+?): (\d+)\.', prompt)
        for src, dst, t in travel_pattern:
            src = src.strip()
            dst = dst.strip()
            travel_times[(src, dst)] = int(t)
        
        # Extract starting location and time
        start_match = re.search(r'You arrive at ([A-Za-z\' ]+?) at (\d+:\d+[AP]M)', prompt)
        if not start_match:
            return None
        start_location = start_match.group(1).strip()
        start_time_str = start_match.group(2)
        start_time = parse_time(start_time_str)
        
        # Extract friend constraints
        friends = []
        friend_pattern = re.findall(
            r'(\w+) will be at ([A-Za-z\' ]+?) from (\d+:\d+[AP]M) to (\d+:\d+[AP]M)\. You\'d like to meet \w+ for a minimum of (\d+) minutes\.',
            prompt
        )
        for name, location, avail_start, avail_end, min_dur in friend_pattern:
            friends.append({
                'name': name,
                'location': location.strip(),
                'avail_start': parse_time(avail_start),
                'avail_end': parse_time(avail_end),
                'min_duration': int(min_dur),
            })
        
        if not friends:
            return None
        
        # Now solve: try all permutations of friends to find the one that meets the most
        # For large numbers of friends, we need a smarter approach
        n = len(friends)
        
        best_schedule = None
        best_count = -1
        
        if n <= 10:
            # Use bitmask DP or try subsets with permutations
            # For up to ~10 friends, we can try all subsets ordered by permutation
            # But 10! is too large. Let's use a smarter approach.
            # We'll use bitmask DP with ordering
            best_schedule = solve_dp(friends, travel_times, start_location, start_time)
        else:
            best_schedule = solve_dp(friends, travel_times, start_location, start_time)
        
        if best_schedule is None or len(best_schedule) == 0:
            return None
        
        # Format output
        result = format_schedule(best_schedule, start_location, start_time, friends, travel_times)
        return result
        
    except Exception as e:
        return None


def parse_time(time_str):
    """Parse time string like '9:00AM' to minutes since midnight."""
    match = re.match(r'(\d+):(\d+)(AM|PM)', time_str)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    ampm = match.group(3)
    if ampm == 'AM':
        if hour == 12:
            hour = 0
    else:  # PM
        if hour != 12:
            hour += 12
    return hour * 60 + minute


def format_time(minutes):
    """Format minutes since midnight to time string like '9:00AM'."""
    h = minutes // 60
    m = minutes % 60
    if h == 0:
        return f"12:{m:02d}AM"
    elif h < 12:
        return f"{h}:{m:02d}AM"
    elif h == 12:
        return f"12:{m:02d}PM"
    else:
        return f"{h-12}:{m:02d}PM"


def solve_dp(friends, travel_times, start_location, start_time):
    """
    Use bitmask DP to find the optimal schedule.
    State: (current_location, visited_mask) -> earliest finish time
    We want to maximize the number of bits set in the mask.
    """
    n = len(friends)
    
    if n > 20:
        # Too many friends for bitmask DP, fall back
        return solve_greedy(friends, travel_times, start_location, start_time)
    
    # State: (mask, last_friend_index) -> (earliest_end_time, path)
    # -1 means we're at start_location
    
    # Initialize: from start, try visiting each friend
    # dp[mask][last] = minimum end time to have visited exactly the friends in mask,
    #                  with 'last' being the last friend visited
    
    INF = float('inf')
    
    # dp[mask][last] = earliest time we finish meeting the last friend
    dp = {}
    parent = {}
    
    # Initial state: at start_location at start_time, no friends visited
    # Try going to each friend first
    for i in range(n):
        f = friends[i]
        key = (start_location, f['location'])
        if key not in travel_times:
            if start_location == f['location']:
                travel = 0
            else:
                continue
        else:
            travel = travel_times[key]
        
        arrive = start_time + travel
        # Can we meet this friend?
        meet_start = max(arrive, f['avail_start'])
        meet_end = meet_start + f['min_duration']
        
        if meet_end > f['avail_end']:
            continue
        
        mask = 1 << i
        if (mask, i) not in dp or meet_end < dp[(mask, i)]:
            dp[(mask, i)] = meet_end
            parent[(mask, i)] = (-1, 0)  # came from start
    
    # Expand states
    # We process in order of popcount to build up
    for popcount in range(1, n):
        # Find all states with this popcount
        states_at_pop = [(k, v) for k, v in dp.items() if bin(k[0]).count('1') == popcount]
        
        for (mask, last), current_time in states_at_pop:
            last_loc = friends[last]['location']
            
            for j in range(n):
                if mask & (1 << j):
                    continue  # already visited
                
                f = friends[j]
                key = (last_loc, f['location'])
                if key not in travel_times:
                    if last_loc == f['location']:
                        travel = 0
                    else:
                        continue
                else:
                    travel = travel_times[key]
                
                arrive = current_time + travel
                meet_start = max(arrive, f['avail_start'])
                meet_end = meet_start + f['min_duration']
                
                if meet_end > f['avail_end']:
                    continue
                
                new_mask = mask | (1 << j)
                if (new_mask, j) not in dp or meet_end < dp[(new_mask, j)]:
                    dp[(new_mask, j)] = meet_end
                    parent[(new_mask, j)] = (mask, last)
    
    # Find the best result: maximum popcount, then minimum end time
    if not dp:
        return []
    
    best_key = None
    best_popcount = -1
    best_time = INF
    
    for (mask, last), end_time in dp.items():
        pc = bin(mask).count('1')
        if pc > best_popcount or (pc == best_popcount and end_time < best_time):
            best_popcount = pc
            best_time = end_time
            best_key = (mask, last)
    
    if best_key is None:
        return []
    
    # Reconstruct path
    path = []
    current = best_key
    while current in parent:
        mask, last = current
        path.append(last)
        prev = parent[current]
        if prev[0] == -1:
            break
        current = (prev[0], prev[1])
    
    path.reverse()
    return path


def solve_greedy(friends, travel_times, start_location, start_time):
    """Greedy fallback for large instances."""
    # Sort by availability end time (earliest deadline first)
    n = len(friends)
    remaining = list(range(n))
    schedule = []
    current_loc = start_location
    current_time = start_time
    
    while remaining:
        best_next = None
        best_end = float('inf')
        
        for i in remaining:
            f = friends[i]
            key = (current_loc, f['location'])
            if key not in travel_times:
                if current_loc == f['location']:
                    travel = 0
                else:
                    continue
            else:
                travel = travel_times[key]
            
            arrive = current_time + travel
            meet_start = max(arrive, f['avail_start'])
            meet_end = meet_start + f['min_duration']
            
            if meet_end <= f['avail_end']:
                if meet_end < best_end:
                    best_end = meet_end
                    best_next = i
        
        if best_next is None:
            break
        
        schedule.append(best_next)
        f = friends[best_next]
        key = (current_loc, f['location'])
        if key not in travel_times:
            travel = 0
        else:
            travel = travel_times[key]
        arrive = current_time + travel
        meet_start = max(arrive, f['avail_start'])
        meet_end = meet_start + f['min_duration']
        current_time = meet_end
        current_loc = f['location']
        remaining.remove(best_next)
    
    return schedule


def format_schedule(path, start_location, start_time, friends, travel_times):
    """Format the schedule as a list of strings."""
    result = []
    result.append(f"You start at {start_location} at {format_time(start_time)}.")
    
    current_loc = start_location
    current_time = start_time
    
    for idx in path:
        f = friends[idx]
        dest = f['location']
        
        # Travel
        key = (current_loc, dest)
        if key in travel_times:
            travel = travel_times[key]
        elif current_loc == dest:
            travel = 0
        else:
            return None
        
        arrive_time = current_time + travel
        
        if travel > 0:
            result.append(f"You travel to {dest} in {travel} minutes and arrive at {format_time(arrive_time)}.")
        
        # Wait if needed
        meet_start = max(arrive_time, f['avail_start'])
        if meet_start > arrive_time:
            result.append(f"You wait until {format_time(meet_start)}.")
        
        meet_end = meet_start + f['min_duration']
        
        result.append(f"You meet {f['name']} for {f['min_duration']} minutes from {format_time(meet_start)} to {format_time(meet_end)}.")
        
        current_loc = dest
        current_time = meet_end
    
    return result
