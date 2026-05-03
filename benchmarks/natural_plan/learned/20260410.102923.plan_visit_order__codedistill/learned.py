"""Auto-generated code-distilled implementation for plan_visit_order."""

import json
import re
from itertools import permutations
from datetime import datetime, timedelta


def plan_visit_order(prompt, data_str):
    try:
        data = json.loads(data_str)
    except:
        return None

    my_location = data["my_location"]
    my_start_time = parse_time(data["my_start_time"])
    friends = data["friends"]
    travel_times = data["travel_times"]

    n = len(friends)
    best_schedule = None
    best_count = 0

    # Try all subsets ordered by size (descending) and all permutations
    for size in range(n, 0, -1):
        if best_count >= size:
            break
        found = False
        for subset in combinations_indices(n, size):
            for perm in permutations(subset):
                schedule = try_schedule(perm, friends, travel_times, my_location, my_start_time)
                if schedule is not None:
                    if len(schedule) > best_count:
                        best_count = len(schedule)
                        best_schedule = schedule
                        if best_count == size == n:
                            return format_output(best_schedule)
                        found = True
        if found and best_count == size:
            break

    if best_schedule is None:
        return 'SOLUTION: []'

    return format_output(best_schedule)


def parse_time(t_str):
    t_str = t_str.strip()
    for fmt in ["%I:%M %p", "%I:%M%p"]:
        try:
            return datetime.strptime(t_str, fmt)
        except:
            continue
    return None


def combinations_indices(n, size):
    if size == 0:
        yield ()
        return
    def _combo(start, remaining):
        if remaining == 0:
            yield ()
            return
        for i in range(start, n):
            for rest in _combo(i + 1, remaining - 1):
                yield (i,) + rest
    yield from _combo(0, size)


def try_schedule(perm, friends, travel_times, start_location, start_time):
    current_time = start_time
    current_location = start_location
    schedule = []

    for idx in perm:
        friend = friends[idx]
        name = friend["name"]
        location = friend["location"]
        avail_from = parse_time(friend["available_from"])
        avail_to = parse_time(friend["available_to"])
        duration = friend["duration_minutes"]

        # Travel to friend's location
        travel_key = f"{current_location}->{location}"
        if current_location == location:
            travel_min = 0
        elif travel_key in travel_times:
            travel_min = travel_times[travel_key]
        else:
            return None

        arrive_time = current_time + timedelta(minutes=travel_min)

        # Meeting starts at max(arrive_time, avail_from)
        meeting_start = max(arrive_time, avail_from)

        # Meeting ends
        meeting_end = meeting_start + timedelta(minutes=duration)

        # Check if meeting fits within availability
        if meeting_end > avail_to:
            return None

        schedule.append(name)
        current_time = meeting_end
        current_location = location

    return schedule


def format_output(schedule):
    result = json.dumps(schedule)
    # Check if output examples have SOLUTION: prefix or not - they vary
    # Looking at examples: some have 'SOLUTION: [...]' and some just '[...]'
    # The function is called as plan(), let's check expected outputs
    # Example 1: 'SOLUTION: ["Margaret", "Robert", "Kimberly", "Rebecca"]'
    # Example 3: starts with '["Kimberly"...' (no SOLUTION prefix)
    # Since the prompt says "Your response should start with 'SOLUTION:'", include it
    return f'SOLUTION: {result}'


def plan(prompt, data_str):
    return plan_visit_order(prompt, data_str)
