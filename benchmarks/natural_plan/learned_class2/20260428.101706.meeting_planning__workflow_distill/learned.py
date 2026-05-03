"""Auto-generated workflow-distilled implementation for meeting_planning.

Calls existing tools from ptools_meeting.
"""

from ptools_meeting import *

import re
from itertools import permutations


def meeting_planning(prompt: str) -> list:
    # Parse the input
    # Extract starting location and time
    start_match = re.search(r'You arrive at (.+?) at (\d+:\d+[AP]M)', prompt)
    if not start_match:
        return None
    start_location = start_match.group(1)
    start_time_str = start_match.group(2)
    start_time = parse_time(start_time_str)
    
    # Extract travel distances
    distances = {}
    dist_pattern = re.findall(r'(.+?) to (.+?): (\d+)\.', prompt)
    for src, dst, mins in dist_pattern:
        src = src.strip()
        dst = dst.strip()
        distances[(src, dst)] = int(mins)
    
    # Extract friend constraints
    # Pattern: "Name will be at Location from Time1 to Time2. You'd like to meet Name for a minimum of X minutes."
    friends = []
    friend_pattern = re.findall(
        r'(\w+) will be at (.+?) from (\d+:\d+[AP]M) to (\d+:\d+[AP]M)\.\s+You\'d like to meet \1 for a minimum of (\d+) minutes\.',
        prompt
    )
    for name, location, avail_start, avail_end, min_minutes in friend_pattern:
        friends.append({
            'name': name,
            'location': location,
            'avail_start': parse_time(avail_start),
            'avail_end': parse_time(avail_end),
            'min_minutes': int(min_minutes),
        })
    
    # Now solve: try all subsets of friends, ordered by permutations, pick the one that meets the most friends
    # For efficiency, if too many friends, use heuristic approaches
    
    n = len(friends)
    
    best_schedule = []
    best_count = 0
    
    # If n is small enough, try all permutations of all subsets
    # But permutations of n friends = n! which is too large for n > 8 or so
    # Let's use a smarter approach: try all permutations but prune early
    
    if n <= 10:
        # Try subsets from largest to smallest
        # For each size, try permutations
        from itertools import combinations
        
        found_max = False
        for size in range(n, 0, -1):
            if found_max:
                break
            for combo in combinations(range(n), size):
                for perm in permutations(combo):
                    schedule = try_schedule(start_location, start_time, perm, friends, distances)
                    if schedule is not None and len(schedule['meetings']) == size:
                        if size > best_count:
                            best_count = size
                            best_schedule = schedule
                            found_max = True
                            break
                        elif size == best_count:
                            # Compare: prefer the one with earlier end or some tiebreaker
                            # Actually, we just need max count
                            pass
                if found_max:
                    break
    else:
        # Use greedy + local search for larger instances
        # Try multiple greedy strategies
        best_schedule, best_count = solve_large(start_location, start_time, friends, distances, n)
    
    if best_schedule is None or best_count == 0:
        return [f'You start at {start_location} at {format_time(start_time)}.']
    
    return format_schedule(best_schedule, start_location, start_time, friends, distances)


def parse_time(time_str: str) -> int:
    """Parse time string like '9:00AM' to minutes since midnight."""
    match = re.match(r'(\d+):(\d+)(AM|PM)', time_str)
    if not match:
        return 0
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


def format_time(minutes: int) -> str:
    """Format minutes since midnight to time string like '9:00AM'."""
    hour = minutes // 60
    minute = minutes % 60
    if hour == 0:
        return f'12:{minute:02d}AM'
    elif hour < 12:
        return f'{hour}:{minute:02d}AM'
    elif hour == 12:
        return f'12:{minute:02d}PM'
    else:
        return f'{hour - 12}:{minute:02d}PM'


def try_schedule(start_location, start_time, perm, friends, distances):
    """Try to schedule friends in the given order. Returns schedule dict or None."""
    current_location = start_location
    current_time = start_time
    meetings = []
    
    for idx in perm:
        f = friends[idx]
        dest = f['location']
        
        # Travel time
        if current_location == dest:
            travel_time = 0
        else:
            key = (current_location, dest)
            if key not in distances:
                return None  # Can't travel there
            travel_time = distances[key]
        
        arrival_time = current_time + travel_time
        
        # Can we meet this friend?
        # Meeting starts at max(arrival_time, avail_start)
        meeting_start = max(arrival_time, f['avail_start'])
        meeting_end = meeting_start + f['min_minutes']
        
        # Must finish before avail_end
        if meeting_end > f['avail_end']:
            return None  # Can't meet this friend
        
        meetings.append({
            'friend_idx': idx,
            'travel_time': travel_time,
            'arrival_time': arrival_time,
            'meeting_start': meeting_start,
            'meeting_end': meeting_end,
            'from_location': current_location,
            'to_location': dest,
        })
        
        current_location = dest
        current_time = meeting_end
    
    return {'meetings': meetings}


def format_schedule(schedule, start_location, start_time, friends, distances):
    """Format a schedule into the expected output format."""
    result = [f'You start at {start_location} at {format_time(start_time)}.']
    
    for m in schedule['meetings']:
        f = friends[m['friend_idx']]
        
        # Travel step (if different location)
        if m['from_location'] != m['to_location']:
            result.append(
                f"You travel to {m['to_location']} in {m['travel_time']} minutes and arrive at {format_time(m['arrival_time'])}."
            )
        
        # Wait step (if needed)
        if m['meeting_start'] > m['arrival_time']:
            result.append(f"You wait until {format_time(m['meeting_start'])}.")
        
        # Meeting step
        result.append(
            f"You meet {f['name']} for {f['min_minutes']} minutes from {format_time(m['meeting_start'])} to {format_time(m['meeting_end'])}."
        )
    
    return result


def solve_large(start_location, start_time, friends, distances, n):
    """Solve for larger instances using greedy + local search."""
    from itertools import combinations, permutations as perms
    
    best_schedule = None
    best_count = 0
    
    # Try greedy: sort by availability start time
    indices_by_start = sorted(range(n), key=lambda i: friends[i]['avail_start'])
    
    # Try greedy with different strategies
    strategies = [
        sorted(range(n), key=lambda i: friends[i]['avail_start']),
        sorted(range(n), key=lambda i: friends[i]['avail_end']),
        sorted(range(n), key=lambda i: friends[i]['avail_end'] - friends[i]['min_minutes']),
    ]
    
    for strategy in strategies:
        # Greedy: try to add friends in this order
        schedule_indices = greedy_build(start_location, start_time, strategy, friends, distances)
        if len(schedule_indices) > best_count:
            sched = try_schedule(start_location, start_time, schedule_indices, friends, distances)
            if sched is not None:
                best_count = len(schedule_indices)
                best_schedule = sched
    
    # Also try all permutations of the best greedy result + neighbors
    # Local search: try swapping, inserting
    if best_count > 0:
        improved = True
        current_indices = [m['friend_idx'] for m in best_schedule['meetings']]
        while improved:
            improved = False
            # Try inserting any missing friend
            missing = [i for i in range(n) if i not in current_indices]
            for m_idx in missing:
                for pos in range(len(current_indices) + 1):
                    new_indices = current_indices[:pos] + [m_idx] + current_indices[pos:]
                    sched = try_schedule(start_location, start_time, new_indices, friends, distances)
                    if sched is not None and len(sched['meetings']) > best_count:
                        best_count = len(sched['meetings'])
                        best_schedule = sched
                        current_indices = new_indices
                        improved = True
                        break
                if improved:
                    break
            
            if not improved:
                # Try swapping
                for i in range(len(current_indices)):
                    for j in range(i + 1, len(current_indices)):
                        new_indices = list(current_indices)
                        new_indices[i], new_indices[j] = new_indices[j], new_indices[i]
                        sched = try_schedule(start_location, start_time, new_indices, friends, distances)
                        if sched is not None and len(sched['meetings']) > best_count:
                            best_count = len(sched['meetings'])
                            best_schedule = sched
                            current_indices = new_indices
                            improved = True
                            break
                    if improved:
                        break
    
    return best_schedule, best_count


def greedy_build(start_location, start_time, order, friends, distances):
    """Greedily build a schedule by trying to add friends in given order."""
    selected = []
    
    for idx in order:
        # Try inserting idx at every position
        best_pos = None
        best_end_time = float('inf')
        
        for pos in range(len(selected) + 1):
            candidate = selected[:pos] + [idx] + selected[pos:]
            sched = try_schedule_quick(start_location, start_time, candidate, friends, distances)
            if sched is not None:
                if best_pos is None or sched < best_end_time:
                    best_pos = pos
                    best_end_time = sched
        
        if best_pos is not None:
            selected = selected[:best_pos] + [idx] + selected[best_pos:]
    
    return selected


def try_schedule_quick(start_location, start_time, perm, friends, distances):
    """Quick check if schedule is feasible. Returns end time or None."""
    current_location = start_location
    current_time = start_time
    
    for idx in perm:
        f = friends[idx]
        dest = f['location']
        
        if current_location == dest:
            travel_time = 0
        else:
            key = (current_location, dest)
            if key not in distances:
                return None
            travel_time = distances[key]
        
        arrival_time = current_time + travel_time
        meeting_start = max(arrival_time, f['avail_start'])
        meeting_end = meeting_start + f['min_minutes']
        
        if meeting_end > f['avail_end']:
            return None
        
        current_location = dest
        current_time = meeting_end
    
    return current_time
