"""Task-specific interfaces for NaturalPlan calendar scheduling.

Decomposition derived from LLM reasoning traces:
1. parse_schedules — extract participants, busy slots, duration, preference
2. find_available_slots — compute free slot intersections
3. select_and_format — pick best slot, format answer
"""

import json
import re
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

        CRITICAL INSTRUCTIONS for 'schedules' and 'preference':
        - If a participant wants to AVOID meetings on a specific day (e.g., "rather not meet on Monday", "can not meet on Tuesday"), add ["0:00", "23:59"] to their busy schedule for that day.
        - If they want to avoid meetings AFTER a certain time (e.g., "after 14:00"), add ["14:00", "23:59"] to their busy schedule for that day.
        - If they want to avoid meetings BEFORE a certain time (e.g., "before 10:00"), add ["0:00", "10:00"] to their busy schedule for that day.
        - Pay attention to multiple days in constraints: "avoid more meetings on Thursday. Friday." means BOTH Thursday and Friday are completely busy ["0:00", "23:59"].
        - DO NOT set global 'preference' based on an individual's avoidances. 'preference' should be "earliest" if the group wants "earliest availability", "latest" if they want "latest availability", else null.

        Use 24-hour format (e.g. "9:00", "15:30", no leading zero on hour). For participants with wide-open calendars, use empty lists.

    Example:
        >>> parse_schedules("Schedule Alice and Bob for 30 min on Monday 9:00 to 17:00. Alice busy 9:00-10:00. Bob has no meetings. Bob would rather not meet on Monday after 14:00.")
        '{"participants": ["Alice", "Bob"], "duration_minutes": 30, "working_hours": ["9:00", "17:00"], "days": ["Monday"], "preference": null, "schedules": {"Alice": {"Monday": [["9:00", "10:00"]]}, "Bob": {"Monday": [["14:00", "23:59"]]}}}'
    """

def parse_time(t_str: str) -> int:
    h, m = map(int, t_str.split(':'))
    return h * 60 + m

def format_time(t_min: int) -> str:
    h = t_min // 60
    m = t_min % 60
    return f"{h}:{m:02d}"

@interface
def find_available_slots_llm(problem_text: str, schedules_json: str) -> str:
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
    """

def find_available_slots(problem_text: str, schedules_json: str) -> str:
    try:
        clean_json = schedules_json.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()
            
        data = json.loads(clean_json)
        duration = int(data.get("duration_minutes", 30))
        wh = data.get("working_hours", ["9:00", "17:00"])
        days = data.get("days", [])
        if not days:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        schedules = data.get("schedules", {})
        
        start_wh = parse_time(str(wh[0]))
        end_wh = parse_time(str(wh[1]))
        
        valid_slots = []
        for day in days:
            for t in range(start_wh, end_wh - duration + 1, 30):
                slot_start = t
                slot_end = t + duration
                
                conflict = False
                for person, schedule in schedules.items():
                    if not isinstance(schedule, dict): continue
                    busy_intervals = schedule.get(day, [])
                    if not isinstance(busy_intervals, list): continue
                    
                    for interval in busy_intervals:
                        if not isinstance(interval, list) or len(interval) < 2:
                            continue
                        try:
                            b_start = parse_time(str(interval[0]))
                            b_end = parse_time(str(interval[1]))
                        except Exception:
                            continue
                            
                        # Two intervals overlap if max(start1, start2) < min(end1, end2)
                        if max(slot_start, b_start) < min(slot_end, b_end):
                            conflict = True
                            break
                    if conflict:
                        break
                        
                if not conflict:
                    valid_slots.append({
                        "day": day,
                        "start": format_time(slot_start),
                        "end": format_time(slot_end)
                    })
        
        # If strict Python intersection finds 0 slots, fallback to LLM
        # to ensure we don't crash the pipeline on datasets with typos/inconsistencies
        if not valid_slots:
            return find_available_slots_llm(problem_text, schedules_json)
            
        return json.dumps(valid_slots)
    except Exception:
        return find_available_slots_llm(problem_text, schedules_json)

@interface
def select_and_format_llm(slots_json: str, preference: str) -> str:
    """Pick the best slot based on preference and format the final answer.

    Args:
        slots_json: The JSON STRING output returned by find_available_slots
            (a JSON array of slot dicts). Pass the raw JSON string as-is.
        preference: Either "earliest" (pick the first slot) or "latest"
            (pick the last slot).

    Returns:
        A string with exactly this format:
        'Here is the proposed time: {Day}, {HH:MM} - {HH:MM}'
    """

def select_and_format(slots_json: str, preference: str) -> str:
    try:
        clean_json = slots_json.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()
            
        slots = json.loads(clean_json)
        if not isinstance(slots, list) or len(slots) == 0:
            raise ValueError("No valid slots extracted")
            
        if preference == "latest":
            slot = slots[-1]
        else:
            slot = slots[0]
            
        return f"Here is the proposed time: {slot['day']}, {slot['start']} - {slot['end']}"
    except Exception:
        return select_and_format_llm(slots_json, preference)

@interface
def calendar_scheduling(prompt: str) -> str:
    """Solve a calendar scheduling problem.

    Given a scheduling problem describing participants, their busy times,
    meeting duration, and any preferences, return a single proposed meeting
    time that satisfies all constraints.

    Args:
        prompt: The full scheduling problem as one string.

    Returns:
        A string with exactly this format:
        'Here is the proposed time: {Day}, {HH:MM} - {HH:MM}'
    """
    ...

def calendar_workflow(prompt: str) -> str:
    schedules = parse_schedules(prompt)
    slots = find_available_slots(prompt, schedules)
    return select_and_format(slots, "earliest")

# --- Auto-generated by orchestration_learner --seed-orchestrate ---
def calendar_scheduling_orchestrated_seed(prompt: str) -> str:
    schedules_json = parse_schedules(prompt)
    slots_json = find_available_slots(prompt, schedules_json)

    # Extract the preference from the JSON string without importing the json module
    compact_json = schedules_json.replace(" ", "")
    if '"preference":"latest"' in compact_json:
        preference = "latest"
    else:
        preference = "earliest"

    return select_and_format(slots_json, preference)