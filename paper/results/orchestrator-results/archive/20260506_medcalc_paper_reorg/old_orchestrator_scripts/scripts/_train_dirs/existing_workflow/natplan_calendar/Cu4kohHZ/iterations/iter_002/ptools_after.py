"""Task-specific interfaces for NaturalPlan calendar scheduling.

Decomposition derived from LLM reasoning traces:
1. parse_schedules — extract participants, busy slots, duration, preference
2. find_available_slots — compute free slot intersections
3. select_and_format — pick best slot, format answer
"""

import json
from datetime import datetime
from secretagent.core import interface


@interface
def parse_schedules(problem_text: str) -> str:
    """Parse a calendar scheduling problem into structured JSON.

    Args:
        problem_text: The ENTIRE scheduling problem description as a single
            string. Pass the whole problem text (participants, their busy
            times, duration, preferences, working hours, etc.) as one
            argument — do NOT split it into multiple arguments.

    Returns:
        A JSON string encoding a dict with these keys:
        - participants: list of participant names
        - duration_minutes: meeting duration (30 or 60)
        - working_hours: [start_str, end_str] e.g. ["9:00", "17:00"]
        - days: list of day names e.g. ["Monday", "Tuesday"]
        - preference: "earliest" or "latest" or null
        - schedules: dict mapping participant name to dict mapping day to
          list of busy intervals e.g. {"Alice": {"Monday": [["9:00","10:00"]]}}

        Use 24-hour format. For participants with wide-open calendars, use empty lists.

    Example:
        >>> parse_schedules("You need to schedule a meeting for Alice and Bob for half an hour on Monday between 9:00 and 17:00. Alice is busy 9:00-10:00. Bob has no meetings.")
        '{"participants": ["Alice", "Bob"], "duration_minutes": 30, "working_hours": ["9:00", "17:00"], "days": ["Monday"], "preference": "earliest", "schedules": {"Alice": {"Monday": [["9:00", "10:00"]]}, "Bob": {"Monday": []}}}'
    """


@interface
def find_available_slots(problem_text: str, schedules_json: str) -> str:
    """Find valid meeting slots that work for all participants.

    Args:
        problem_text: The original problem text (same string you passed to
            parse_schedules).
        schedules_json: The JSON STRING output returned by parse_schedules.
            Pass the raw JSON string as-is — do NOT parse it into a dict first.

    Returns:
        A JSON string encoding a list of slot dicts, sorted by day order
        then start time:
        [{"day": str, "start": str, "end": str}, ...]
        Each slot is at least duration_minutes long. Use 24-hour "HH:MM" format.

    Example:
        >>> find_available_slots(
        ...     "Schedule Alice and Bob for 30 min on Monday 9-17. Alice busy 9:00-10:00.",
        ...     '{"participants": ["Alice","Bob"], "duration_minutes": 30, "working_hours": ["9:00","17:00"], "days": ["Monday"], "schedules": {"Alice": {"Monday": [["9:00","10:00"]]}, "Bob": {"Monday": []}}}')
        '[{"day": "Monday", "start": "10:00", "end": "10:30"}, {"day": "Monday", "start": "10:30", "end": "11:00"}]'
    """


@interface
def select_and_format(problem_text: str, valid_slots_json: str) -> str:
    """Pick the best slot from the valid options and format the final answer.

    Args:
        problem_text: The original scheduling problem text (which includes examples 
            and ends with the target TASK). Use the patterns in the examples to 
            deduce the hidden rules for which slot to pick.
        valid_slots_json: A JSON string containing a list of mathematically valid
            slots. You MUST pick your final proposed time from this list, UNLESS
            a slot violates a negative constraint from the problem_text (e.g., 
            "avoid Monday", "can not meet before 12:00"). If a slot violates a 
            constraint, discard it. If all slots are discarded or the list is empty, 
            deduce the correct slot directly from the problem_text.

    Returns:
        A string with exactly this format:
        'Here is the proposed time: {Day}, {HH:MM} - {HH:MM}'
    """


@interface(method="direct")
def calendar_scheduling(prompt: str) -> str:
    """Solve a calendar scheduling problem end-to-end.

    ALWAYS use this tool to solve the scheduling problem. It will automatically
    parse schedules, find intersections, validate constraints, and format the output.

    Args:
        prompt: The full scheduling problem as one string.

    Returns:
        A string with exactly this format:
        'Here is the proposed time: {Day}, {HH:MM} - {HH:MM}'
    """
    schedules = parse_schedules(prompt)
    slots = find_available_slots(prompt, schedules)
    
    try:
        slots_list = json.loads(slots)
        sched_data = json.loads(schedules)
        valid = []
        for s in slots_list:
            try:
                st = datetime.strptime(s["start"], "%H:%M")
                en = datetime.strptime(s["end"], "%H:%M")
                # Fix formatting to ensure strict string matching (e.g., 09:00 -> 9:00)
                s["start"] = f"{st.hour}:{st.strftime('%M')}"
                s["end"] = f"{en.hour}:{en.strftime('%M')}"
                
                # Check slot against explicitly parsed schedules to eliminate LLM hallucinations
                overlap = False
                for p, days in sched_data.get("schedules", {}).items():
                    for b in days.get(s["day"], []):
                        if len(b) == 2:
                            try:
                                bst = datetime.strptime(b[0], "%H:%M")
                                ben = datetime.strptime(b[1], "%H:%M")
                            except Exception:
                                continue
                            if max(st, bst) < min(en, ben):
                                overlap = True
                                break
                    if overlap: 
                        break
                        
                if not overlap:
                    valid.append(s)
            except Exception:
                # If slot parsing fails, keep it to allow LLM to handle it gracefully
                valid.append(s)
                
        if valid:
            slots = json.dumps(valid)
        else:
            # If all slots were hallucinated overlaps, pass empty list so LLM knows to deduce it natively
            slots = "[]"
    except Exception:
        pass

    return select_and_format(prompt, slots)