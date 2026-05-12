"""Task-specific interfaces for NaturalPlan meeting planning.

Decomposition derived from LLM reasoning traces:
1. parse_meeting_info — extract locations, friends, travel times, availability
2. plan_visit_order — determine optimal visit order to maximize meetings
3. build_meeting_plan — simulate schedule step-by-step and format answer
"""

from secretagent.core import interface


@interface
def parse_meeting_info(problem_text: str) -> str:
    """Parse a meeting-planning problem into structured JSON.

    Args:
        problem_text: The ENTIRE meeting-planning problem as a single string
            (your starting location/time, travel distances between locations,
            each friend's location / availability window / desired meeting
            duration, etc.). Pass the whole problem text as one argument —
            do NOT split it into multiple arguments.

    Returns:
        A JSON string encoding a dict with these keys:
        - my_location: starting location name
        - my_start_time: start time string e.g. "9:00 AM"
        - friends: list of dicts, each with:
            name, location, available_from, available_to, duration_minutes
        - travel_times: dict mapping "LocationA->LocationB" to minutes (int)

    Example:
        >>> parse_meeting_info("You arrive at Alamo Square at 9:00 AM. James will be at Nob Hill from 9:00 AM to 5:30 PM; you want to meet for 30 min. Travel: Alamo Square to Nob Hill: 11 min.")
        '{"my_location": "Alamo Square", "my_start_time": "9:00 AM", "friends": [{"name": "James", "location": "Nob Hill", "available_from": "9:00 AM", "available_to": "5:30 PM", "duration_minutes": 30}], "travel_times": {"Alamo Square->Nob Hill": 11}}'
    """


@interface
def plan_visit_order(problem_text: str, info_json: str) -> str:
    """Determine the optimal order of friends to visit to maximize meetings.

    Args:
        problem_text: The original problem text (same string you passed to
            parse_meeting_info).
        info_json: The JSON STRING output returned by parse_meeting_info.
            Pass the raw JSON string as-is — do NOT parse it into a dict first.

    Returns:
        A JSON string encoding an ordered list of friend names (strings).
        Consider travel times, each friend's availability window, and
        required meeting durations; use greedy or exhaustive search to
        maximize the number of friends met.

    Example:
        >>> plan_visit_order("...", '{"friends": [...], ...}')
        '["James", "Nancy", "William"]'
    """


@interface
def build_meeting_plan(problem_text: str, info_json: str, order_json: str) -> str:
    """Build a step-by-step meeting schedule and format the final answer.

    Args:
        problem_text: The original problem text.
        info_json: The JSON STRING output from parse_meeting_info. Pass the
            raw JSON string as-is.
        order_json: The JSON STRING output from plan_visit_order (a JSON
            array of friend names). Pass the raw JSON string as-is.

    Returns:
        The final answer as a string that MUST start with 'SOLUTION:',
        followed by step lines in EXACTLY these formats (note times use
        'HH:MMAM' or 'HH:MMPM' with no space before AM/PM):
        'You start at {location} at {time}.'
        'You travel to {location} in {N} minutes and arrive at {time}.'
        'You wait until {time}.'
        'You meet {name} for {N} minutes from {time} to {time}.'

        Simulate the schedule: for each friend in order, compute travel time,
        wait if needed, meet for the required duration. Skip friends who
        cannot be met within their availability window.

    Example:
        >>> build_meeting_plan("...", '{"my_location": "Alamo Square", ...}', '["James"]')
        'SOLUTION: You start at Alamo Square at 9:00AM. You travel to Nob Hill in 11 minutes and arrive at 9:11AM. You meet James for 30 minutes from 9:11AM to 9:41AM.'
    """


@interface
def meeting_planning(prompt: str) -> str:
    """Solve a meeting-planning problem.

    Given a problem describing your start location/time, friend locations
    and availability windows, travel times, and desired meeting durations,
    produce a schedule that maximizes the number of friends met.

    Args:
        prompt: The full meeting-planning problem as one string.

    Returns:
        A string starting with 'SOLUTION:' followed by action lines in
        EXACTLY these formats (times use 'HH:MMAM' or 'HH:MMPM' with no
        space before AM/PM):
        'You start at {location} at {time}.'
        'You travel to {location} in {N} minutes and arrive at {time}.'
        'You wait until {time}.'
        'You meet {name} for {N} minutes from {time} to {time}.'

    Example:
        'SOLUTION: You start at Marina District at 9:00AM. You travel to Mission District in 20 minutes and arrive at 9:20AM. You wait until 10:30AM. You meet Stephanie for 120 minutes from 10:30AM to 12:30PM.'
    """
    ...


def meeting_workflow(prompt: str) -> str:
    info = parse_meeting_info(prompt)
    order = plan_visit_order(prompt, info)
    return build_meeting_plan(prompt, info, order)
