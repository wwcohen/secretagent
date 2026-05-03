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
            Note: The 'friends' list inside this JSON is sorted chronologically 
            by availability start time to help you plan.

    Returns:
        First, think step-by-step inside <thinking> tags. Construct ONE 
        highly-optimized timeline step-by-step to maximize the TOTAL COUNT of 
        friends met.
        
        CRITICAL RULES TO MAXIMIZE MEETINGS:
        1. Maintain a running clock and current location. At each step, explicitly 
           list ALL unvisited friends who can still fit into the remaining day.
        2. Choose the next friend to minimize wasted time (travel + wait). 
           Prioritize friends with short durations (15-60 mins) and early deadlines.
        3. BEWARE LONG MEETINGS: Friends requiring 105 or 120 minutes consume a lot 
           of time. Strongly consider SKIPPING them if doing so allows you to fit 
           2 or 3 shorter meetings instead. Your primary goal is to maximize the NUMBER of friends met.
        4. DO NOT STOP PLANNING EARLY: You MUST continue your schedule into the late 
           evening (e.g., 8:00 PM - 10:30 PM). Always check if remaining friends can 
           be visited before midnight. Never leave the evening empty if someone is available.
        5. Verify time math: Current Time + Travel + Wait + Duration <= Available To.
        6. CAUTION: Travel times are NOT symmetric! Always use the exact A->B time.
        
        After closing </thinking>, output ONLY a JSON string encoding an 
        ordered list of friend names (strings). Do not write 'SOLUTION:'.

    Example:
        >>> plan_visit_order("...", '{"friends": [...], ...}')
        '<thinking>...</thinking>\n["James", "Nancy", "William"]'
    """


@interface
def build_meeting_plan(problem_text: str, info_json: str, order_json: str) -> str:
    """Build a step-by-step meeting schedule and format the final answer.

    Args:
        problem_text: The original problem text.
        info_json: The JSON STRING output from parse_meeting_info. Pass the
            raw JSON string as-is.
        order_json: The JSON STRING output from plan_visit_order. Pass the
            raw JSON string as-is.

    Returns:
        First, output your timeline calculations inside <thinking> tags. 
        After your thinking, output the final answer as a string that MUST 
        start EXACTLY with 'SOLUTION:', followed by step lines in EXACTLY 
        these formats (note times use 'HH:MMAM' or 'HH:MMPM' with no space 
        before AM/PM):
        'You start at {location} at {time}.'
        'You travel to {location} in {N} minutes and arrive at {time}.'
        'You wait until {time}.'
        'You meet {name} for {N} minutes from {time} to {time}.'

        Simulate the schedule: for each friend in order, compute travel time,
        wait if needed, meet for the required duration. 

        RULES:
        1. Skip friends who cannot be met for their FULL required duration within their availability window.
        2. ONLY output a 'You wait until {time}.' line if your arrival time is STRICTLY BEFORE the friend's availability starts. If you arrive at or after their availability starts, DO NOT include a wait line. (e.g. 1:15PM is AFTER 12:45PM).
        3. CAUTION: Travel times are NOT symmetric! The time from A to B may be different from B to A. Look up the exact travel time for the specific direction you are traveling.
        4. Time math must be exact. 60 minutes = 1 hour. Pay close attention to AM vs PM transitions (11:59AM -> 12:00PM).

    Example:
        >>> build_meeting_plan("...", '{"my_location": "Alamo Square", ...}', '["James"]')
        '<thinking>...</thinking>\nSOLUTION: You start at Alamo Square at 9:00AM. You travel to Nob Hill in 11 minutes and arrive at 9:11AM. You meet James for 30 minutes from 9:11AM to 9:41AM.'
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


# --- Auto-generated by orchestration_learner --seed-orchestrate ---
def meeting_planning_orchestrated_seed(prompt: str) -> str:
    import re
    import json
    
    info_json = parse_meeting_info(prompt)
    info_json = re.sub(r'```(?:json)?', '', info_json, flags=re.IGNORECASE).strip()
    
    try:
        info = json.loads(info_json)
        if "friends" in info and isinstance(info["friends"], list):
            def parse_time(t_str):
                m = re.search(r'(\d+):(\d+)\s*(AM|PM)', str(t_str), re.IGNORECASE)
                if not m: return 9999
                h, mins, ampm = int(m.group(1)), int(m.group(2)), m.group(3).upper()
                if h == 12 and ampm == 'AM': h = 0
                elif h < 12 and ampm == 'PM': h += 12
                return h * 60 + mins
                
            info["friends"].sort(key=lambda x: (
                parse_time(x.get("available_from", "")),
                parse_time(x.get("available_to", "")),
                x.get("duration_minutes", 999)
            ))
            info_json = json.dumps(info)
    except Exception:
        pass
    
    order_json = plan_visit_order(prompt, info_json)
    order_clean = re.sub(r'<thinking>.*?</thinking>', '', order_json, flags=re.DOTALL).strip()
    order_clean = re.sub(r'```(?:json)?', '', order_clean, flags=re.IGNORECASE).strip()
    order_clean = order_clean.replace("SOLUTION:", "").strip()
    
    plan = build_meeting_plan(prompt, info_json, order_clean)
    plan_clean = re.sub(r'<thinking>.*?</thinking>', '', plan, flags=re.DOTALL).strip()
    
    if not plan_clean.startswith("SOLUTION:"):
        plan_clean = plan_clean.lstrip()
        if plan_clean.startswith("You start"):
            plan_clean = "SOLUTION: " + plan_clean
            
    return plan_clean