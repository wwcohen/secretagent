"""Task-specific interfaces for NaturalPlan calendar scheduling.

Decomposition derived from LLM reasoning traces:
1. parse_schedules — extract participants, busy slots, duration, preference
2. find_available_slots — compute free slot intersections
3. select_and_format — pick best slot, format answer
"""

import json
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

        CRITICAL INSTRUCTION FOR "schedules":
        If a participant has a negative constraint (e.g., "would rather not meet on Monday", "can not meet on Tuesday before 12:00", "would like to avoid more meetings on Wednesday"), YOU MUST ADD A BUSY INTERVAL to their schedule to block out that day or time! 
        - To block an entire day, add ["00:00", "23:59"].
        - To block after a time (e.g., "after 14:30"), add ["14:30", "23:59"].
        - To block before a time (e.g., "before 12:00"), add ["00:00", "12:00"].

        Use 24-hour format. For participants with wide-open calendars, use empty lists.

    Example:
        >>> parse_schedules("You need to schedule a meeting for Alice and Bob for half an hour on Monday between 9:00 and 17:00. Alice is busy 9:00-10:00. Bob has no meetings. Bob would rather not meet on Monday after 15:00.")
        '{"participants": ["Alice", "Bob"], "duration_minutes": 30, "working_hours": ["9:00", "17:00"], "days": ["Monday"], "preference": "earliest", "schedules": {"Alice": {"Monday": [["9:00", "10:00"]]}, "Bob": {"Monday": [["15:00", "23:59"]]}}}'
    """


@interface(method="direct")
def find_available_slots(problem_text: str, schedules_json: str) -> str:
    """Find valid meeting slots that work for all participants."""
    schedules_json = schedules_json.strip()
    if schedules_json.startswith("```json"):
        schedules_json = schedules_json[7:]
    elif schedules_json.startswith("```"):
        schedules_json = schedules_json[3:]
    if schedules_json.endswith("```"):
        schedules_json = schedules_json[:-3]
    schedules_json = schedules_json.strip()
    
    try:
        data = json.loads(schedules_json)
    except Exception:
        return "[]"
    
    participants = data.get("participants", [])
    try:
        duration_minutes = int(data.get("duration_minutes", 30))
    except:
        duration_minutes = 30
        
    working_hours = data.get("working_hours", ["9:00", "17:00"])
    if not isinstance(working_hours, list) or len(working_hours) != 2:
        working_hours = ["9:00", "17:00"]
        
    days = data.get("days", [])
    if not days:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        
    schedules = data.get("schedules", {})

    def parse_int(s):
        return int(''.join(c for c in str(s) if c.isdigit()))

    def time_to_mins(t_str):
        parts = str(t_str).split(':')
        return parse_int(parts[0]) * 60 + parse_int(parts[1])

    def mins_to_time(m):
        return f"{m // 60}:{m % 60:02d}"

    try:
        work_start = time_to_mins(working_hours[0])
        work_end = time_to_mins(working_hours[1])
    except:
        work_start = 9 * 60
        work_end = 17 * 60

    day_order = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7}
    days = sorted(days, key=lambda d: day_order.get(d, 99))

    available_slots = []
    all_participants = set(participants) | set(schedules.keys())

    for day in days:
        start_m = work_start
        while start_m + duration_minutes <= work_end:
            end_m = start_m + duration_minutes
            
            conflict = False
            for p in all_participants:
                p_sched = schedules.get(p, {})
                day_busy = p_sched.get(day, [])
                if not isinstance(day_busy, list):
                    continue
                for interval in day_busy:
                    if not isinstance(interval, list) or len(interval) != 2:
                        continue
                    try:
                        b_start = time_to_mins(interval[0])
                        b_end = time_to_mins(interval[1])
                    except:
                        continue
                    
                    if max(start_m, b_start) < min(end_m, b_end):
                        conflict = True
                        break
                if conflict:
                    break
            
            if not conflict:
                available_slots.append({
                    "day": day,
                    "start": mins_to_time(start_m),
                    "end": mins_to_time(end_m)
                })
            
            start_m += 30

    return json.dumps(available_slots)


@interface(method="direct")
def select_and_format(slots_json: str, preference: str) -> str:
    """Pick the best slot based on preference and format the final answer."""
    slots_json = slots_json.strip()
    if slots_json.startswith("```json"):
        slots_json = slots_json[7:]
    elif slots_json.startswith("```"):
        slots_json = slots_json[3:]
    if slots_json.endswith("```"):
        slots_json = slots_json[:-3]
    slots_json = slots_json.strip()

    try:
        slots = json.loads(slots_json)
    except Exception:
        slots = []
        
    if not slots:
        return "No slots available to select from."
        
    if str(preference).strip().lower() == "latest":
        best_slot = slots[-1]
    else:
        best_slot = slots[0]
        
    return f"Here is the proposed time: {best_slot['day']}, {best_slot['start']} - {best_slot['end']}"


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