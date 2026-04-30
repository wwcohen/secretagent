"""Auto-generated workflow-distilled implementation for meeting_planning.

Calls existing tools from ptools_meeting.
"""

from ptools_meeting import *

import re
from itertools import permutations
from datetime import datetime, timedelta

def meeting_planning(prompt: str) -> str:
    # Parse the problem
    travel_times = {}
    travel_pattern = re.findall(r'(.+?) to (.+?): (\d+)\.', prompt)
    for src, dst, mins in travel_pattern:
        travel_times[(src.strip(), dst.strip())] = int(mins)
    
    # Parse starting location and time
    arrive_match = re.search(r'You arrive at (.+?) at (\d+:\d+[AP]M)', prompt)
    if not arrive_match:
        return None
    start_location = arrive_match.group(1).strip()
    start_time_str = arrive_match.group(2)
    start_time = parse_time(start_time_str)
    
    # Parse friend constraints
    friends = []
    friend_pattern = re.findall(
        r'(\w+) will be at (.+?) from (\d+:\d+[AP]M) to (\d+:\d+[AP]M)\. You\'d like to meet \w+ for a minimum of (\d+) minutes\.',
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
    
    # Get all locations
    locations = set()
    for src, dst in travel_times:
        locations.add(src)
        locations.add(dst)
    
    # Try all permutations of friends to find the one that meets the most
    n = len(friends)
    
    best_schedule = None
    best_count = -1
    
    # For large n, we can't try all permutations of all subsets
    # We'll try all permutations of subsets, starting from largest
    # For n up to ~9, we need a smarter approach
    
    if n <= 10:
        # Try all subsets ordered by size (largest first), and all permutations
        from itertools import combinations
        
        for size in range(n, 0, -1):
            if best_count >= size:
                break  # Can't do better
            for combo in combinations(range(n), size):
                for perm in permutations(combo):
                    schedule = simulate_schedule(start_location, start_time, perm, friends, travel_times)
                    if schedule is not None and len(schedule) > best_count:
                        best_count = len(schedule)
                        best_schedule = schedule
                        if best_count == size == n:
                            break
                if best_count == size == n:
                    break
            if best_count == size:
                break
    else:
        # For larger n, use greedy + local search
        # Try multiple greedy strategies
        best_schedule, best_count = large_n_search(start_location, start_time, friends, travel_times, n)
    
    if best_schedule is None or best_count == 0:
        return None
    
    return format_schedule(start_location, start_time, best_schedule)


def parse_time(time_str):
    """Parse time string like '9:00AM' to minutes since midnight."""
    time_str = time_str.strip()
    match = re.match(r'(\d+):(\d+)(AM|PM)', time_str)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    ampm = match.group(3)
    if ampm == 'AM':
        if hours == 12:
            hours = 0
    else:
        if hours != 12:
            hours += 12
    return hours * 60 + minutes


def format_time(minutes):
    """Format minutes since midnight to time string like '9:00AM'."""
    hours = minutes // 60
    mins = minutes % 60
    if hours == 0:
        return f"12:{mins:02d}AM"
    elif hours < 12:
        return f"{hours}:{mins:02d}AM"
    elif hours == 12:
        return f"12:{mins:02d}PM"
    else:
        return f"{hours-12}:{mins:02d}PM"


def simulate_schedule(start_location, start_time, friend_order, friends, travel_times):
    """Simulate visiting friends in given order. Returns list of schedule entries or None if infeasible."""
    current_location = start_location
    current_time = start_time
    schedule = []
    
    for idx in friend_order:
        friend = friends[idx]
        dest = friend['location']
        
        # Get travel time
        if current_location == dest:
            travel = 0
        else:
            key = (current_location, dest)
            if key not in travel_times:
                return None  # No route
            travel = travel_times[key]
        
        arrive_time = current_time + travel
        
        # Earliest we can start meeting
        meeting_start = max(arrive_time, friend['avail_start'])
        meeting_end = meeting_start + friend['min_duration']
        
        # Check if meeting fits within availability
        if meeting_end > friend['avail_end']:
            return None  # Can't meet this friend
        
        schedule.append({
            'friend_idx': idx,
            'travel_time': travel,
            'arrive_time': arrive_time,
            'wait_until': friend['avail_start'] if arrive_time < friend['avail_start'] else None,
            'meeting_start': meeting_start,
            'meeting_end': meeting_end,
            'destination': dest,
        })
        
        current_location = dest
        current_time = meeting_end
    
    return schedule


def format_schedule(start_location, start_time, schedule):
    """Format schedule into the expected output string."""
    lines = ["SOLUTION:"]
    lines.append(f"You start at {start_location} at {format_time(start_time)}.")
    
    current_location = start_location
    
    for entry in schedule:
        dest = entry['destination']
        travel = entry['travel_time']
        arrive = entry['arrive_time']
        wait = entry['wait_until']
        m_start = entry['meeting_start']
        m_end = entry['meeting_end']
        friend_idx = entry['friend_idx']
        
        if travel > 0:
            lines.append(f"You travel to {dest} in {travel} minutes and arrive at {format_time(arrive)}.")
        
        if wait is not None and arrive < wait:
            lines.append(f"You wait until {format_time(wait)}.")
        
        # Get friend name from the entry - we need to pass friends info
        name = entry.get('friend_name', '')
        duration = m_end - m_start
        lines.append(f"You meet {name} for {duration} minutes from {format_time(m_start)} to {format_time(m_end)}.")
        
        current_location = dest
    
    return '\n'.join(lines)


def large_n_search(start_location, start_time, friends, travel_times, n):
    """Search for best schedule with larger number of friends."""
    from itertools import combinations, permutations
    
    best_schedule = None
    best_count = 0
    
    # Try subsets from largest to smallest
    for size in range(n, 0, -1):
        if best_count >= size:
            break
        
        found = False
        for combo in combinations(range(n), size):
            # Try some heuristic orderings
            # Sort by availability start
            sorted_by_start = sorted(combo, key=lambda i: friends[i]['avail_start'])
            # Sort by availability end
            sorted_by_end = sorted(combo, key=lambda i: friends[i]['avail_end'])
            # Sort by latest start (avail_end - min_duration)
            sorted_by_latest = sorted(combo, key=lambda i: friends[i]['avail_end'] - friends[i]['min_duration'])
            
            orderings_to_try = [sorted_by_start, sorted_by_end, sorted_by_latest]
            
            # Also try permutations if size is small enough
            if size <= 8:
                for perm in permutations(combo):
                    schedule = simulate_schedule(start_location, start_time, perm, friends, travel_times)
                    if schedule is not None and len(schedule) > best_count:
                        best_count = len(schedule)
                        best_schedule = schedule
                        # Add friend names
                        for entry in best_schedule:
                            entry['friend_name'] = friends[entry['friend_idx']]['name']
                        if best_count == size:
                            found = True
                            break
            else:
                for ordering in orderings_to_try:
                    schedule = simulate_schedule(start_location, start_time, ordering, friends, travel_times)
                    if schedule is not None and len(schedule) > best_count:
                        best_count = len(schedule)
                        best_schedule = schedule
                        for entry in best_schedule:
                            entry['friend_name'] = friends[entry['friend_idx']]['name']
                        if best_count == size:
                            found = True
                            break
            
            if found:
                break
        
        if found:
            break
    
    return best_schedule, best_count


# Override the main function to fix friend name propagation
def meeting_planning(prompt: str) -> str:
    # Parse the problem
    travel_times = {}
    travel_pattern = re.findall(r'(.+?) to (.+?): (\d+)\.', prompt)
    for src, dst, mins in travel_pattern:
        travel_times[(src.strip(), dst.strip())] = int(mins)
    
    # Parse starting location and time
    arrive_match = re.search(r'You arrive at (.+?) at (\d+:\d+[AP]M)', prompt)
    if not arrive_match:
        return None
    start_location = arrive_match.group(1).strip()
    start_time_str = arrive_match.group(2)
    start_time = parse_time(start_time_str)
    if start_time is None:
        return None
    
    # Parse friend constraints
    friends = []
    constraints_section = prompt.split('CONSTRAINTS:')[1] if 'CONSTRAINTS:' in prompt else prompt
    
    friend_pattern = re.findall(
        r'(\w+) will be at (.+?) from (\d+:\d+[AP]M) to (\d+:\d+[AP]M)\. You\'d like to meet \w+ for a minimum of (\d+) minutes\.',
        constraints_section
    )
    for name, location, avail_start, avail_end, min_dur in friend_pattern:
        as_time = parse_time(avail_start)
        ae_time = parse_time(avail_end)
        if as_time is None or ae_time is None:
            return None
        friends.append({
            'name': name,
            'location': location.strip(),
            'avail_start': as_time,
            'avail_end': ae_time,
            'min_duration': int(min_dur),
        })
    
    n = len(friends)
    if n == 0:
        return None
    
    best_schedule = None
    best_count = -1
    
    from itertools import combinations, permutations
    
    # Determine max permutations we can handle
    # n! for n=9 is 362880, for n=10 is 3628800
    # With subsets, sum of P(n,k) for k from n down
    # We'll be smart: try largest subsets first
    
    import math
    
    for size in range(n, 0, -1):
        if best_count >= size:
            break
        
        found_optimal = False
        
        num_combos = math.comb(n, size)
        num_perms_per = math.perm(size, size)
        total = num_combos * num_perms_per
        
        if total <= 500000:
            # Enumerate all
            for combo in combinations(range(n), size):
                for perm in permutations(combo):
                    schedule = simulate_schedule(start_location, start_time, perm, friends, travel_times)
                    if schedule is not None and len(schedule) > best_count:
                        best_count = len(schedule)
                        best_schedule = schedule
                        for entry in best_schedule:
                            entry['friend_name'] = friends[entry['friend_idx']]['name']
                        if best_count == n:
                            found_optimal = True
                            break
                if found_optimal:
                    break
        else:
            # Too many to enumerate exhaustively
            # Use heuristic orderings for each combo
            for combo in combinations(range(n), size):
                # Try multiple orderings
                orderings = get_heuristic_orderings(combo, friends, start_location, start_time, travel_times)
                for ordering in orderings:
                    schedule = simulate_schedule(start_location, start_time, ordering, friends, travel_times)
                    if schedule is not None and len(schedule) > best_count:
                        best_count = len(schedule)
                        best_schedule = schedule
                        for entry in best_schedule:
                            entry['friend_name'] = friends[entry['friend_idx']]['name']
                        if best_count == size:
                            found_optimal = True
                            break
                if found_optimal:
                    break
        
        if found_optimal or best_count >= size:
            break
    
    if best_schedule is None or best_count == 0:
        return None
    
    return format_schedule(start_location, start_time, best_schedule)


def get_heuristic_orderings(combo, friends, start_location, start_time, travel_times):
    """Generate multiple heuristic orderings for a given combination of friends."""
    combo_list = list(combo)
    orderings = []
    
    # Sort by availability start
    orderings.append(tuple(sorted(combo_list, key=lambda i: friends[i]['avail_start'])))
    # Sort by availability end
    orderings.append(tuple(sorted(combo_list, key=lambda i: friends[i]['avail_end'])))
    # Sort by latest possible start (avail_end - min_duration)
    orderings.append(tuple(sorted(combo_list, key=lambda i: friends[i]['avail_end'] - friends[i]['min_duration'])))
    # Sort by availability end - min_duration (deadline)
    orderings.append(tuple(sorted(combo_list, key=lambda i: (friends[i]['avail_end'] - friends[i]['min_duration'], friends[i]['avail_start']))))
    
    # Greedy nearest neighbor from start
    orderings.append(tuple(greedy_nearest(combo_list, friends, start_location, start_time, travel_times)))
    
    # Remove duplicates
    seen = set()
    unique = []
    for o in orderings:
        if o not in seen:
            seen.add(o)
            unique.append(o)
    
    return unique


def greedy_nearest(combo_list, friends, start_location, start_time, travel_times):
    """Greedy ordering by earliest feasible meeting."""
    remaining = list(combo_list)
    order = []
    current_loc = start_location
    current_time = start_time
    
    while remaining:
        best_idx = None
        best_end_time = float('inf')
        
        for idx in remaining:
            friend = friends[idx]
            dest = friend['location']
            if current_loc == dest:
                travel = 0
            else:
                key = (current_loc, dest)
                if key not in travel_times:
                    continue
                travel = travel_times[key]
            
            arrive = current_time + travel
            meeting_start = max(arrive, friend['avail_start'])
            meeting_end = meeting_start + friend['min_duration']
            
            if meeting_end <= friend['avail_end']:
                if meeting_end < best_end_time:
                    best_end_time = meeting_end
                    best_idx = idx
        
        if best_idx is None:
            # Can't meet anyone else, just append remaining
            order.extend(remaining)
            break
        
        order.append(best_idx)
        remaining.remove(best_idx)
        friend = friends[best_idx]
        dest = friend['location']
        if current_loc == dest:
            travel = 0
        else:
            travel = travel_times.get((current_loc, dest), 0)
        arrive = current_time + travel
        meeting_start = max(arrive, friend['avail_start'])
        current_time = meeting_start + friend['min_duration']
        current_loc = dest
    
    return order
