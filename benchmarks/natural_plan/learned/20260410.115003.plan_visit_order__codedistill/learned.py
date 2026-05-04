"""Auto-generated code-distilled implementation for plan_visit_order."""

import json
import re
from itertools import permutations
from datetime import datetime, timedelta


def parse_time(time_str):
    """Parse time string like '9:00 AM' into minutes since midnight."""
    time_str = time_str.strip()
    dt = datetime.strptime(time_str, "%I:%M %p")
    return dt.hour * 60 + dt.minute


def plan_visit_order(prompt, data_str):
    try:
        data = json.loads(data_str)
    except:
        return None

    my_location = data["my_location"]
    my_start_time = parse_time(data["my_start_time"])
    friends = data["friends"]
    travel_times = data["travel_times"]

    def get_travel_time(loc_from, loc_to):
        if loc_from == loc_to:
            return 0
        key = f"{loc_from}->{loc_to}"
        return travel_times.get(key, float('inf'))

    def simulate(order):
        """Simulate visiting friends in the given order. Returns True if feasible."""
        current_time = my_start_time
        current_location = my_location

        for idx in order:
            friend = friends[idx]
            travel = get_travel_time(current_location, friend["location"])
            arrival_time = current_time + travel
            available_from = parse_time(friend["available_from"])
            available_to = parse_time(friend["available_to"])
            duration = friend["duration_minutes"]

            # Start meeting at max(arrival_time, available_from)
            meeting_start = max(arrival_time, available_from)

            # Check if we can meet for the required duration within their availability
            meeting_end = meeting_start + duration

            if meeting_end > available_to:
                return False, 0

            current_time = meeting_end
            current_location = friend["location"]

        return True, len(order)

    n = len(friends)
    best_count = 0
    best_order = []

    # Try all subsets ordered by size (largest first), and for each subset try permutations
    # For efficiency, try from largest subset down and stop early if we find a valid one
    
    from itertools import combinations

    # For large n, we need to be smarter - but let's try with pruning
    # Try subsets from largest to smallest
    for size in range(n, 0, -1):
        if size <= best_count:
            break
        for combo in combinations(range(n), size):
            # Try all permutations of this combo
            found = False
            for perm in permutations(combo):
                feasible, count = simulate(perm)
                if feasible and count > best_count:
                    best_count = count
                    best_order = list(perm)
                    if best_count == size:
                        found = True
                        break
            if found and best_count == size:
                break
        if best_count == size:
            break

    result_names = [friends[i]["name"] for i in best_order]
    return f'SOLUTION: {json.dumps(result_names)}'
