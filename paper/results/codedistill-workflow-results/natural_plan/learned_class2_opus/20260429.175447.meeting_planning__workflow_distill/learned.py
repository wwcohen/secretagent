"""Auto-generated workflow-distilled implementation for meeting_planning.

Calls existing tools from ptools_meeting.
"""

from ptools_meeting import *

import re
import itertools
from datetime import datetime, timedelta

def meeting_planning(prompt: str) -> list:
    """Solve a meeting planning problem to meet as many friends as possible."""
    
    # Parse the problem
    try:
        result = _solve_meeting_planning(prompt)
        if result is not None:
            return result
    except Exception:
        pass
    
    # Fallback to LLM
    try:
        raw = build_meeting_plan(prompt)
        if raw is not None:
            return _parse_solution_output(raw)
    except Exception:
        pass
    
    return None


def _parse_time(s):
    """Parse time string like '9:00AM', '10:15PM' into minutes from midnight."""
    s = s.strip().upper()
    match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', s)
    if not match:
        return None
    h, m, ampm = int(match.group(1)), int(match.group(2)), match.group(3)
    if ampm == 'AM':
        if h == 12:
            h = 0
    else:
        if h != 12:
            h += 12
    return h * 60 + m


def _format_time(minutes):
    """Format minutes from midnight into time string like '9:00AM'."""
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


def _solve_meeting_planning(prompt):
    # Parse travel distances
    distances = {}
    dist_pattern = re.findall(r'([A-Za-z\s\'\-]+?) to ([A-Za-z\s\'\-]+?):\s*(\d+)', prompt)
    for src, dst, d in dist_pattern:
        src = src.strip()
        dst = dst.strip()
        distances[(src, dst)] = int(d)
    
    # Parse starting location and time
    start_match = re.search(r'You arrive at (.+?) at (\d{1,2}:\d{2}[AP]M)', prompt)
    if not start_match:
        return None
    start_location = start_match.group(1).strip()
    start_time = _parse_time(start_match.group(2))
    if start_time is None:
        return None
    
    # Parse friend constraints
    friends = []
    friend_pattern = re.findall(
        r'(\w+) will be at (.+?) from (\d{1,2}:\d{2}[AP]M) to (\d{1,2}:\d{2}[AP]M)\.\s*You\'d like to meet \w+ for a minimum of (\d+) minutes',
        prompt
    )
    for name, location, start_avail, end_avail, min_dur in friend_pattern:
        sa = _parse_time(start_avail)
        ea = _parse_time(end_avail)
        md = int(min_dur)
        if sa is None or ea is None:
            return None
        friends.append({
            'name': name,
            'location': location.strip(),
            'start_avail': sa,
            'end_avail': ea,
            'min_duration': md
        })
    
    if not friends:
        return None
    
    # Verify all distances exist for needed routes
    all_locations = set([start_location] + [f['location'] for f in friends])
    
    n = len(friends)
    
    # For each permutation of friends (or subset if too many), find best schedule
    # With n friends, we try all subsets ordered by size (descending), and for each size,
    # try permutations to find one that works
    
    best_schedule = None
    best_count = 0
    
    # For efficiency, limit search
    if n <= 10:
        # Try to find schedules meeting all friends first, then fewer
        best_schedule = _find_best_schedule(start_location, start_time, friends, distances, n)
    else:
        # Too many friends, use heuristic
        best_schedule = _find_best_schedule_heuristic(start_location, start_time, friends, distances)
    
    if best_schedule is None:
        return None
    
    return best_schedule


def _find_best_schedule(start_location, start_time, friends, distances, n):
    """Try all subsets from largest to smallest, find valid schedules."""
    
    # Try from all friends down to 1
    for size in range(n, 0, -1):
        best_for_size = None
        best_for_size_score = None  # We want max friends, then earliest finish
        
        for combo in itertools.combinations(range(n), size):
            # Try all permutations of this combo
            # For large combos, this is expensive - limit
            perms = itertools.permutations(combo)
            
            # Limit permutations for large sizes
            max_perms = 100000 if size <= 8 else 50000
            count = 0
            
            for perm in perms:
                count += 1
                if count > max_perms:
                    break
                
                schedule = _try_schedule(start_location, start_time, friends, distances, perm)
                if schedule is not None:
                    # Calculate end time for comparison
                    if best_for_size is None:
                        best_for_size = schedule
                    else:
                        # Prefer the schedule - we just need any valid one with this count
                        # but prefer one that ends earlier (more flexibility)
                        best_for_size = schedule  # Take latest found (could improve heuristic)
                    return schedule  # Return first valid schedule with max friends
            
        if best_for_size is not None:
            return best_for_size
    
    return None


def _try_schedule(start_location, start_time, friends, distances, perm):
    """Try to build a schedule visiting friends in the given permutation order."""
    steps = []
    current_location = start_location
    current_time = start_time
    
    steps.append(f"You start at {start_location} at {_format_time(start_time)}.")
    
    for idx in perm:
        friend = friends[idx]
        dest = friend['location']
        
        # Get travel time
        if current_location == dest:
            travel_time = 0
        else:
            key = (current_location, dest)
            if key not in distances:
                return None
            travel_time = distances[key]
        
        # Travel
        if travel_time > 0:
            arrive_time = current_time + travel_time
            steps.append(f"You travel to {dest} in {travel_time} minutes and arrive at {_format_time(arrive_time)}.")
            current_time = arrive_time
            current_location = dest
        
        # Check if we can meet this friend
        # We need to arrive before their availability ends, with enough time for min_duration
        meet_start = max(current_time, friend['start_avail'])
        meet_end = meet_start + friend['min_duration']
        
        if meet_end > friend['end_avail']:
            return None  # Can't meet this friend
        
        # Add wait if needed
        if meet_start > current_time:
            steps.append(f"You wait until {_format_time(meet_start)}.")
        
        steps.append(f"You meet {friend['name']} for {friend['min_duration']} minutes from {_format_time(meet_start)} to {_format_time(meet_end)}.")
        
        current_time = meet_end
    
    return steps


def _find_best_schedule_heuristic(start_location, start_time, friends, distances):
    """Use greedy/heuristic approach for large instances."""
    n = len(friends)
    
    # Sort friends by end availability (earliest deadline first) as a heuristic
    # Try multiple orderings
    
    orderings = []
    
    # Ordering 1: by earliest start availability
    order1 = sorted(range(n), key=lambda i: friends[i]['start_avail'])
    orderings.append(order1)
    
    # Ordering 2: by earliest end availability  
    order2 = sorted(range(n), key=lambda i: friends[i]['end_avail'])
    orderings.append(order2)
    
    # Ordering 3: by earliest possible meeting time (start_avail)
    # then by end time
    order3 = sorted(range(n), key=lambda i: (friends[i]['start_avail'], friends[i]['end_avail']))
    orderings.append(order3)
    
    best_schedule = None
    best_count = 0
    
    for base_order in orderings:
        # Try greedy: pick friends in this order, skip if can't meet
        schedule, count = _greedy_schedule(start_location, start_time, friends, distances, base_order)
        if count > best_count:
            best_count = count
            best_schedule = schedule
    
    # Also try branch and bound with the best heuristic ordering
    if n <= 15:
        # Try permutations with pruning
        result = _branch_and_bound(start_location, start_time, friends, distances, best_count)
        if result is not None:
            return result
    
    return best_schedule


def _greedy_schedule(start_location, start_time, friends, distances, order):
    """Greedily build schedule following given order, skipping impossible friends."""
    steps = []
    current_location = start_location
    current_time = start_time
    met_count = 0
    
    steps.append(f"You start at {start_location} at {_format_time(start_time)}.")
    
    for idx in order:
        friend = friends[idx]
        dest = friend['location']
        
        if current_location == dest:
            travel_time = 0
        else:
            key = (current_location, dest)
            if key not in distances:
                continue
            travel_time = distances[key]
        
        arrive_time = current_time + travel_time
        meet_start = max(arrive_time, friend['start_avail'])
        meet_end = meet_start + friend['min_duration']
        
        if meet_end > friend['end_avail']:
            continue
        
        if travel_time > 0:
            steps.append(f"You travel to {dest} in {travel_time} minutes and arrive at {_format_time(arrive_time)}.")
        
        if meet_start > arrive_time:
            steps.append(f"You wait until {_format_time(meet_start)}.")
        
        steps.append(f"You meet {friend['name']} for {friend['min_duration']} minutes from {_format_time(meet_start)} to {_format_time(meet_end)}.")
        
        current_time = meet_end
        current_location = dest
        met_count += 1
    
    return steps, met_count


def _branch_and_bound(start_location, start_time, friends, distances, min_count):
    """Branch and bound to find schedule meeting more friends than min_count."""
    n = len(friends)
    best = [None]
    best_count = [min_count]
    
    def search(current_loc, current_time, visited, steps):
        remaining = [i for i in range(n) if i not in visited]
        
        # Bound: even if we could meet all remaining, would it beat best?
        if len(visited) + len(remaining) <= best_count[0]:
            # Only continue if we can potentially beat
            pass  # Still try current state
        
        # Record current state if better
        if len(visited) > best_count[0]:
            best_count[0] = len(visited)
            best[0] = list(steps)
        elif len(visited) == best_count[0] and best[0] is None:
            best[0] = list(steps)
        
        # Pruning: if we can't possibly beat best
        if len(visited) + len(remaining) <= best_count[0]:
            return
        
        for idx in remaining:
            friend = friends[idx]
            dest = friend['location']
            
            if current_loc == dest:
                travel_time = 0
            else:
                key = (current_loc, dest)
                if key not in distances:
                    continue
                travel_time = distances[key]
            
            arrive_time = current_time + travel_time
            meet_start = max(arrive_time, friend['start_avail'])
            meet_end = meet_start + friend['min_duration']
            
            if meet_end > friend['end_avail']:
                continue
            
            new_steps = list(steps)
            if travel_time > 0:
                new_steps.append(f"You travel to {dest} in {travel_time} minutes and arrive at {_format_time(arrive_time)}.")
            if meet_start > arrive_time:
                new_steps.append(f"You wait until {_format_time(meet_start)}.")
            new_steps.append(f"You meet {friend['name']} for {friend['min_duration']} minutes from {_format_time(meet_start)} to {_format_time(meet_end)}.")
            
            search(dest, meet_end, visited | {idx}, new_steps)
    
    initial_steps = [f"You start at {start_location} at {_format_time(start_time)}."]
    search(start_location, start_time, set(), initial_steps)
    
    return best[0]


def _parse_solution_output(raw):
    """Parse LLM output into list of step strings."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        # Try to find SOLUTION: prefix
        text = raw
        if 'SOLUTION:' in text:
            text = text.split('SOLUTION:', 1)[1].strip()
        
        lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
        # Filter to only relevant lines
        result = []
        for line in lines:
            # Remove leading numbers/bullets
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            line = re.sub(r'^[-*]\s*', '', line)
            line = line.strip()
            if line.startswith('You '):
                result.append(line)
        return result if result else None
    return None
