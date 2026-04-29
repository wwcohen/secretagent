"""Auto-generated end-to-end implementation for meeting_planning."""

import re
from itertools import permutations
from datetime import datetime, timedelta


def meeting_planning(input_text):
    parsed = parse_input(input_text)
    if parsed is None:
        return None
    solution = solve(parsed)
    if solution is None:
        return None
    return format_output(solution)


def parse_input(text):
    # Extract starting location and time
    start_match = re.search(r'You arrive at (.+?) at (\d+:\d+[AP]M)', text)
    if not start_match:
        return None
    start_location = start_match.group(1)
    start_time = parse_time(start_match.group(2))

    # Extract travel distances
    distances = {}
    dist_pattern = re.findall(r'([A-Za-z\' \-]+?) to ([A-Za-z\' \-]+?): (\d+)', text)
    for src, dst, mins in dist_pattern:
        src = src.strip()
        dst = dst.strip()
        distances[(src, dst)] = int(mins)

    # Extract friend constraints
    friends = []
    friend_pattern = re.findall(
        r'(\w+) will be at (.+?) from (\d+:\d+[AP]M) to (\d+:\d+[AP]M)\. You\'d like to meet \w+ for a minimum of (\d+) minutes',
        text
    )
    for name, location, start, end, duration in friend_pattern:
        friends.append({
            'name': name,
            'location': location.strip(),
            'start': parse_time(start),
            'end': parse_time(end),
            'min_duration': int(duration)
        })

    return {
        'start_location': start_location,
        'start_time': start_time,
        'distances': distances,
        'friends': friends
    }


def parse_time(time_str):
    """Parse time string like '9:00AM' to minutes since midnight."""
    match = re.match(r'(\d+):(\d+)(AM|PM)', time_str)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    period = match.group(3)
    if period == 'AM':
        if hours == 12:
            hours = 0
    else:
        if hours != 12:
            hours += 12
    return hours * 60 + minutes


def format_time(minutes):
    """Convert minutes since midnight to time string like '9:00AM'."""
    hours = minutes // 60
    mins = minutes % 60
    if hours == 0:
        return f"12:{mins:02d}AM"
    elif hours < 12:
        return f"{hours}:{mins:02d}AM"
    elif hours == 12:
        return f"12:{mins:02d}PM"
    else:
        return f"{hours - 12}:{mins:02d}PM"


def solve(parsed):
    start_location = parsed['start_location']
    start_time = parsed['start_time']
    distances = parsed['distances']
    friends = parsed['friends']
    n = len(friends)

    if n == 0:
        return {
            'start_location': start_location,
            'start_time': start_time,
            'steps': []
        }

    # We need to find the ordering of a subset of friends that maximizes the count of friends met
    # For each subset and permutation, simulate the schedule

    # Since n can be up to ~10, we need an efficient approach
    # Use bitmask DP or try permutations with pruning

    # For up to 10 friends, we can use bitmask DP
    # State: (current_location, bitmask of visited friends) -> earliest finish time
    # But we need to track the actual path

    # Let's use BFS/DFS with memoization
    # State: (location, visited_mask) -> min time to reach this state
    # Then we can reconstruct

    locations = set()
    locations.add(start_location)
    for f in friends:
        locations.add(f['location'])

    # DP approach: state = (current_location, visited_mask)
    # Value = minimum current time after visiting all in mask
    # We want to maximize popcount(mask), then minimize end time

    # Initialize
    best_for_state = {}  # (location, mask) -> (current_time, path)

    initial_state = (start_location, 0)
    # path is list of (friend_index, arrive_time, meet_start, meet_end)
    best_for_state[initial_state] = (start_time, [])

    best_result = (0, float('inf'), [])  # (count, end_time, path)

    # BFS by expanding one friend at a time
    # Use a priority queue or just iterate

    # Let's use a different approach: iterate through states
    from collections import deque

    queue = deque()
    queue.append((start_location, 0, start_time, []))

    # To avoid exponential blowup, we need to prune
    # best_for_state: (location, mask) -> best_time (minimum current_time)
    best_time_for_state = {}
    best_time_for_state[(start_location, 0)] = start_time

    while queue:
        cur_loc, mask, cur_time, path = queue.popleft()

        count = bin(mask).count('1')

        # Check if this is a candidate for best result
        if count > best_result[0] or (count == best_result[0] and cur_time < best_result[1]):
            best_result = (count, cur_time, path[:])

        # Try to visit each unvisited friend
        for i, friend in enumerate(friends):
            if mask & (1 << i):
                continue

            dest = friend['location']
            if cur_loc == dest:
                travel_time = 0
            else:
                key = (cur_loc, dest)
                if key not in distances:
                    continue
                travel_time = distances[key]

            arrive_time = cur_time + travel_time
            friend_start = friend['start']
            friend_end = friend['end']
            min_dur = friend['min_duration']

            # Can we meet this friend?
            meet_start = max(arrive_time, friend_start)
            meet_end = meet_start + min_dur

            if meet_end > friend_end:
                continue  # Can't meet this friend

            new_mask = mask | (1 << i)
            new_time = meet_end
            new_state = (dest, new_mask)

            if new_state in best_time_for_state and best_time_for_state[new_state] <= new_time:
                continue

            best_time_for_state[new_state] = new_time

            new_path = path + [(i, arrive_time, meet_start, meet_end)]
            queue.append((dest, new_mask, new_time, new_path))

    # Reconstruct from best_result
    _, _, best_path = best_result

    steps = []
    cur_loc = start_location
    for (fi, arrive_time, meet_start, meet_end) in best_path:
        friend = friends[fi]
        dest = friend['location']
        if cur_loc == dest:
            travel_time = 0
        else:
            travel_time = distances[(cur_loc, dest)]
        steps.append({
            'type': 'travel',
            'from': cur_loc,
            'to': dest,
            'travel_time': travel_time,
            'arrive_time': arrive_time
        })
        if meet_start > arrive_time:
            steps.append({
                'type': 'wait',
                'until': meet_start
            })
        steps.append({
            'type': 'meet',
            'name': friend['name'],
            'duration': friend['min_duration'],
            'start': meet_start,
            'end': meet_end
        })
        cur_loc = dest

    return {
        'start_location': start_location,
        'start_time': start_time,
        'steps': steps
    }


def format_output(solution):
    result = []
    result.append(f"You start at {solution['start_location']} at {format_time(solution['start_time'])}.")

    for step in solution['steps']:
        if step['type'] == 'travel':
            result.append(
                f"You travel to {step['to']} in {step['travel_time']} minutes and arrive at {format_time(step['arrive_time'])}."
            )
        elif step['type'] == 'wait':
            result.append(f"You wait until {format_time(step['until'])}.")
        elif step['type'] == 'meet':
            result.append(
                f"You meet {step['name']} for {step['duration']} minutes from {format_time(step['start'])} to {format_time(step['end'])}."
            )

    return result
