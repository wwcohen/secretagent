"""Auto-generated workflow-distilled implementation for meeting_planning.

Tools from /tmp/induced_ptools_v4g/natplan_meeting_induced.py are inlined below.
"""

"""Induced ptools for NaturalPlan meeting (seed=42).

Auto-generated from results/20260414.033600.meeting_react_train_seed42/results.jsonl.
Model: together_ai/deepseek-ai/DeepSeek-V3.
Do not edit — regenerate via generate_induced_configs.py.
"""

from secretagent.core import implement_via
from ptools_common import _REACT_STATE


@implement_via('simulate')
def _define_meeting_problem_impl(prompt: str, focus: str) -> str:
    """
    Analyzes a meeting planning problem description to extract key constraints and structure them for optimization.

    Extracts:
    - Starting location and time
    - Friends' locations, availability windows, and minimum meeting durations
    - Travel time matrix between all locations
    - Any additional constraints or preferences

    Returns a structured JSON-like string containing:
    {
      "start": {"location": str, "time": str},
      "friends": [
        {"name": str, "location": str, "window_start": str, "window_end": str, "min_duration": int}
      ],
      "travel_times": {
        "location1-location2": int,
        ...
      }
    }

    Pay attention to:
    - Exact time formats (AM/PM, 24-hour)
    - Window boundaries (inclusive/exclusive)
    - Minimum duration requirements
    - Travel time symmetry (A→B may differ from B→A)
    - All possible location pairs in the travel matrix

    Returns:
    Example output structure:
    {
      "start": {"location": "Fisherman's Wharf", "time": "9:00AM"},
      "friends": [
        {"name": "Michelle", "location": "Bayview", "window_start": "7:45PM", "window_end": "9:15PM", "min_duration": 90},
        {"name": "James", "location": "Embarcadero", "window_start": "3:45PM", "window_end": "5:15PM", "min_duration": 75}
      ],
      "travel_times": {
        "Fisherman's Wharf-Embarcadero": 8,
        "Fisherman's Wharf-Bayview": 26,
        "Embarcadero-Bayview": 21,
        "Bayview-Embarcadero": 19,
        "Embarcadero-Fisherman's Wharf": 6,
        "Bayview-Fisherman's Wharf": 25
      }
    }
    """


def define_meeting_problem(focus: str) -> str:
    """Extracts and structures meeting planning constraints from a problem description.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _define_meeting_problem_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _request_travel_times_impl(prompt: str, focus: str) -> str:
    """
    Extracts and returns travel time information between locations from the provided travel-time matrix.
    The function focuses on travel times relevant to the specified focus (e.g., a person, location, or constraint).
    The agent should pay attention to:
    - Symmetry of travel times (if not provided, assume symmetric)
    - Travel time units (consistent with meeting duration)
    - Direct connections vs. multi-hop routes (if matrix includes indirect paths)
    - Any constraints affecting travel (e.g., traffic patterns, time-dependent routes)

    Returns:
    A structured string listing travel times for pairs involving the focus. If focus is a person, returns times from their location to others. If focus is a location, returns times from it to all other locations. If focus is general (e.g., "all"), returns the full travel-time matrix.

    Example output for focus="Alice":
    {
      "travel_times": {
        "Alice->Bob": 15,
        "Alice->Charlie": 20,
        "Alice->David": 25
      }
    }
    """


def request_travel_times(focus: str) -> str:
    """Requests travel time information between specified locations to evaluate meeting feasibility.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _request_travel_times_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _propose_meeting_schedule_impl(prompt: str, focus: str) -> str:
    """
    Extracts meeting constraints from the problem description and proposes an optimal schedule.

    Parses:
    - Starting location and time
    - Friend locations, availability windows, and minimum meeting durations
    - Travel time matrix between locations

    Reasoning:
    - Prioritizes meeting as many friends as possible
    - Ensures meetings occur within specified availability windows
    - Accounts for travel time between locations
    - Ensures minimum meeting duration requirements are met
    - Handles waiting time before meetings if needed
    - Optimizes schedule to maximize total meetings

    Returns:
    A structured schedule with:
    - Start time and location
    - Sequence of meetings with arrival/departure times
    - Travel segments with durations
    - Total meeting time for each friend
    - Confirmation that minimum durations are met

    Example output structure:
    \"\"\"
    Start at [location] at [time].
    Travel to [location] ([duration] min), arrive at [time].
    Meet [friend] from [start] to [end] ([duration] min).
    Travel to [location] ([duration] min), arrive at [time].
    ...
    This schedule allows meeting [number] friends for their minimum durations.
    \"\"\"

    Note: Focus parameter can specify a particular friend, location, or constraint
    to prioritize in the scheduling optimization.
    """


def propose_meeting_schedule(focus: str) -> str:
    """Proposes an optimal meeting schedule that maximizes the number of friends met within their availability windows while accounting for travel time.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _propose_meeting_schedule_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _verify_constraints_impl(prompt: str, focus: str) -> str:
    """
    This function analyzes a meeting planning prompt to extract and validate constraints related to a specific focus. It searches for all mentions of the focus (e.g., a person's name, a location) and extracts associated constraints such as availability windows, minimum meeting durations, and travel times. The function then performs basic validation, checking for the existence of the focus and ensuring its constraints are well-defined (e.g., time windows are valid, durations are positive).

    The response is structured as a plain text summary containing:
    1. A confirmation of whether the focus was found.
    2. A list of all constraints directly associated with the focus.
    3. A list of any potential constraint violations or missing information.
    4. Any other relevant constraints (e.g., travel times) that involve the focus.

    Attention should be paid to:
    - Ensuring the focus (e.g., a friend's name) is correctly identified in the prompt.
    - Correctly parsing time windows (start and end times) and durations.
    - Identifying hard constraints that cannot be violated.
    - Noting any dependencies or conflicts with other parts of the schedule.

    Returns:
    A structured plain text string summarizing the findings.

    Example output for focus='Betty':
    "Focus 'Betty' found. Constraints: Availability from 09:00 to 11:00, minimum meeting duration 30 minutes. Located at CityA. Travel time from your location (Home) to CityA is 15 minutes. No constraint violations detected."
    """


def verify_constraints(focus: str) -> str:
    """Extracts and validates constraints related to a specific focus (person, location, time, etc.) within a meeting planning problem.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _verify_constraints_impl(_REACT_STATE["prompt"], focus)


@implement_via('simulate')
def _analyze_constraints_and_requirements_impl(prompt: str, focus: str) -> str:
    """
    Analyzes the constraints and requirements for scheduling meetings with friends.

    This function parses the problem description to extract:
    - Starting location and time
    - List of friends with their locations, availability windows, and minimum meeting durations
    - Travel time matrix between locations
    - Any other scheduling constraints mentioned

    The function focuses on the specified aspect (friend, location, constraint type)
    and evaluates feasibility considering:
    - Arrival/departure times within availability windows
    - Minimum meeting duration requirements
    - Travel times between locations
    - Potential schedule conflicts

    Returns:
    A structured text analysis containing:
    - List of identified constraints
    - Analysis of the focused aspect
    - Timeline calculations for potential meetings
    - Feasibility assessment for meeting the focused friend/constraint
    - Any identified conflicts or limitations

    Example return structure:
    \"\"\"
    Constraints Analysis:
    - Start: Chinatown at 9:00AM
    - Friends: Anthony (Financial District, 10:00AM-12:00PM, 60 min)
    - Travel times: Chinatown→Financial District: 15 min

    Focus: Anthony
    - Earliest arrival: 9:15AM (15 min travel)
    - Meeting window: 10:00AM-12:00PM
    - Minimum duration: 60 min
    - Feasible meeting: Arrive 10:00AM, depart 11:00AM
    - Total meeting time: 60 minutes
    \"\"\"
    """


def analyze_constraints_and_requirements(focus: str) -> str:
    """Analyzes temporal constraints, travel times, and availability windows to determine feasible meeting schedules.

    Args:
        focus: what aspect to reason about (e.g. a person,
               a city, a time window, a constraint type).
    """
    return _analyze_constraints_and_requirements_impl(_REACT_STATE["prompt"], focus)


import re

def meeting_planning(*args, **kwargs) -> str:
    # Safely extract the input text
    if args:
        text = args[0]
    elif kwargs:
        text = next(iter(kwargs.values()))
    else:
        return None
        
    if not isinstance(text, str):
        return None

    # Parse travel times
    travel_times = {}
    for line in text.split('\n'):
        match = re.match(r'^(.+?)\s+to\s+([^:]+):\s*(\d+)\.', line.strip())
        if match:
            u, v, t = match.groups()
            u = u.strip()
            v = v.strip()
            if u not in travel_times:
                travel_times[u] = {}
            travel_times[u][v] = int(t)
            
    # Parse the entire constraints block
    match = re.search(r'CONSTRAINTS:\s*(.*)', text, re.DOTALL)
    if not match:
        return None
    constraints_text = match.group(1)
    
    # Parse the start location and time
    start_match = re.search(r'You arrive at (.*?)\s*at (\d{1,2}:\d{2}[AP]M)\.', constraints_text)
    if not start_match:
        return None
        
    start_loc = start_match.group(1).strip()
    start_time_str = start_match.group(2)
    
    def parse_time(t_str):
        if not t_str: return 0
        match = re.match(r'(\d+):(\d+)([AP]M)', t_str)
        if not match: return 0
        h, m, ampm = match.groups()
        h = int(h)
        m = int(m)
        if ampm == 'PM' and h != 12:
            h += 12
        if ampm == 'AM' and h == 12:
            h = 0
        return h * 60 + m
        
    def format_time(t_min):
        t_min = t_min % (24 * 60)
        h = t_min // 60
        m = t_min % 60
        ampm = 'AM'
        if h >= 12:
            ampm = 'PM'
            if h > 12:
                h -= 12
        if h == 0:
            h = 12
        return f"{h}:{m:02d}{ampm}"

    start_time = parse_time(start_time_str)
    
    # Parse friend meeting constraints
    friend_matches = re.finditer(r"([A-Za-z]+)\s+will be at\s+(.*?)\s+from\s+(\d{1,2}:\d{2}[AP]M)\s+to\s+(\d{1,2}:\d{2}[AP]M)\.\s+You'd like to meet \1 for a minimum of (\d+)\s+minutes\.", constraints_text)
    friends = []
    for m in friend_matches:
        name = m.group(1).strip()
        loc = m.group(2).strip()
        fs = parse_time(m.group(3))
        fe = parse_time(m.group(4))
        dur = int(m.group(5))
        friends.append({
            'name': name,
            'loc': loc,
            'start': fs,
            'end': fe,
            'dur': dur
        })
        
    if not friends:
        return None
        
    n = len(friends)
    best_schedule = []
    best_num_friends = -1
    best_end_time = float('inf')
    
    # Memoization cache for pruning suboptimal branches
    memo = {}
    
    # Depth-first search to find the optimal schedule
    def dfs(curr_loc, curr_time, visited_mask, schedule):
        nonlocal best_schedule, best_num_friends, best_end_time
        
        # Prune if we've reached this state at an earlier or equal time
        state = (curr_loc, visited_mask)
        if state in memo and memo[state] <= curr_time:
            return
        memo[state] = curr_time

        num_visited = len(schedule)
        
        # We optimize for maximum friends met, with earliest finish time as a tie-breaker
        if num_visited > best_num_friends:
            best_num_friends = num_visited
            best_schedule = list(schedule)
            best_end_time = curr_time
        elif num_visited == best_num_friends:
            if curr_time < best_end_time:
                best_end_time = curr_time
                best_schedule = list(schedule)
                
        if num_visited == n:
            return
            
        for i in range(n):
            if not (visited_mask & (1 << i)):
                f = friends[i]
                nxt_loc = f['loc']
                
                tt = 0
                if curr_loc != nxt_loc:
                    if curr_loc in travel_times and nxt_loc in travel_times[curr_loc]:
                        tt = travel_times[curr_loc][nxt_loc]
                    else:
                        continue # Skip if unreachable
                        
                arrive_time = curr_time + tt
                meet_start = max(arrive_time, f['start'])
                meet_end = meet_start + f['dur']
                
                # Check if the meeting completes within the friend's availability window
                if meet_end <= f['end']:
                    schedule.append((i, tt, arrive_time, meet_start, meet_end))
                    dfs(nxt_loc, meet_end, visited_mask | (1 << i), schedule)
                    schedule.pop()

    # Initiate DFS
    dfs(start_loc, start_time, 0, [])
    
    if best_num_friends <= 0:
        return None
        
    # Generate the strict required output format exactly
    lines = []
    lines.append("SOLUTION:")
    lines.append(f"You start at {start_loc} at {format_time(start_time)}.")
    
    curr_loc = start_loc
    curr_time = start_time
    
    for step in best_schedule:
        idx, tt, arrive_time, meet_start, meet_end = step
        f = friends[idx]
        nxt_loc = f['loc']
        
        if curr_loc != nxt_loc:
            lines.append(f"You travel to {nxt_loc} in {tt} minutes and arrive at {format_time(arrive_time)}.")
            curr_time = arrive_time
            
        if curr_time < meet_start:
            lines.append(f"You wait until {format_time(meet_start)}.")
            
        lines.append(f"You meet {f['name']} for {f['dur']} minutes from {format_time(meet_start)} to {format_time(meet_end)}.")
        
        curr_loc = nxt_loc
        curr_time = meet_end
        
    return "\n".join(lines)
