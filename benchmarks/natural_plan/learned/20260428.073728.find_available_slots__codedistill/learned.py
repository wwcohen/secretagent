"""Auto-generated code-distilled implementation for find_available_slots."""

import json
import re
from datetime import datetime, timedelta

def find_available_slots(problem_text, schedules_json):
    try:
        data = json.loads(schedules_json)
    except (json.JSONDecodeError, TypeError):
        return None
    
    participants = data.get("participants", [])
    duration = data.get("duration_minutes", 30)
    working_hours = data.get("working_hours", ["9:00", "17:00"])
    days = data.get("days", [])
    preference = data.get("preference")
    schedules = data.get("schedules", {})
    
    def time_to_minutes(t):
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    
    def minutes_to_time(m):
        h = m // 60
        mi = m % 60
        return f"{h:02d}:{mi:02d}"
    
    work_start = time_to_minutes(working_hours[0])
    work_end = time_to_minutes(working_hours[1])
    
    # Parse constraints from problem_text
    # Look for "do not want to meet on X" or "would rather not meet on X"
    # Look for "can not meet on X before Y" or "cannot meet on X before Y"
    # Look for "do not want to meet on X after Y"
    
    excluded_days_per_participant = {}
    before_constraints = {}  # (participant, day) -> earliest allowed time
    after_constraints = {}   # (participant, day) -> latest allowed time (must meet before this)
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Parse various constraint patterns from problem_text
    text = problem_text
    
    # Pattern: "X do not want to meet on DAY" or "X would rather not meet on DAY"
    for pattern in [
        r'(\w+)\s+(?:do not want to|would rather not|does not want to|doesn\'t want to|prefers not to)\s+meet\s+on\s+(' + '|'.join(day_names) + r')',
        r'(\w+)\s+(?:do not want to|would rather not|does not want to)\s+meet\s+on\s+(' + '|'.join(day_names) + r')',
    ]:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            name = m.group(1)
            day = m.group(2)
            if name not in excluded_days_per_participant:
                excluded_days_per_participant[name] = set()
            excluded_days_per_participant[name].add(day)
    
    # Pattern: "X can not meet on DAY before TIME" or "X cannot meet on DAY before TIME"
    for pattern in [
        r'(\w+)\s+(?:can\s*not|cannot)\s+meet\s+on\s+(' + '|'.join(day_names) + r')\s+before\s+(\d{1,2}:\d{2})',
    ]:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            name = m.group(1)
            day = m.group(2)
            time_val = m.group(3)
            key = (name, day)
            t = time_to_minutes(time_val)
            before_constraints[key] = max(before_constraints.get(key, 0), t)
    
    # Pattern: "X do not want to meet on DAY after TIME"
    for pattern in [
        r'(\w+)\s+(?:do not want to|does not want to|would rather not)\s+meet\s+on\s+(' + '|'.join(day_names) + r')\s+after\s+(\d{1,2}:\d{2})',
    ]:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            name = m.group(1)
            day = m.group(2)
            time_val = m.group(3)
            key = (name, day)
            t = time_to_minutes(time_val)
            after_constraints[key] = min(after_constraints.get(key, work_end), t)
    
    # Also check: "X would rather not meet on DAY" (already covered above)
    # Check for "X do not want to meet on Monday" without day-specific time
    
    all_slots = []
    
    day_order = {d: i for i, d in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])}
    
    for day in days:
        # Check if any participant has excluded this day entirely
        day_excluded = False
        for name in participants:
            if name in excluded_days_per_participant and day in excluded_days_per_participant[name]:
                day_excluded = True
                break
        if day_excluded:
            continue
        
        # Determine effective working hours for this day considering constraints
        effective_start = work_start
        effective_end = work_end
        
        for name in participants:
            key = (name, day)
            if key in before_constraints:
                effective_start = max(effective_start, before_constraints[key])
            if key in after_constraints:
                effective_end = min(effective_end, after_constraints[key])
        
        if effective_end - effective_start < duration:
            continue
        
        # Collect all busy intervals for all participants on this day
        busy_intervals = []
        for name in participants:
            if name in schedules and day in schedules[name]:
                for slot in schedules[name][day]:
                    start_m = time_to_minutes(slot[0])
                    end_m = time_to_minutes(slot[1])
                    # Clamp to working hours
                    start_m = max(start_m, effective_start)
                    end_m = min(end_m, effective_end)
                    if start_m < end_m:
                        busy_intervals.append((start_m, end_m))
        
        # Merge busy intervals
        busy_intervals.sort()
        merged = []
        for s, e in busy_intervals:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        
        # Find free intervals
        free_intervals = []
        prev_end = effective_start
        for s, e in merged:
            if s > prev_end:
                free_intervals.append((prev_end, s))
            prev_end = max(prev_end, e)
        if prev_end < effective_end:
            free_intervals.append((prev_end, effective_end))
        
        # Generate slots of exact duration from free intervals
        for fs, fe in free_intervals:
            if fe - fs >= duration:
                # Generate all possible slots of the required duration
                slot_start = fs
                while slot_start + duration <= fe:
                    all_slots.append({
                        "day": day,
                        "start": minutes_to_time(slot_start),
                        "end": minutes_to_time(slot_start + duration)
                    })
                    slot_start += 30  # increment by 30 minutes
    
    # Sort by day order then start time
    all_slots.sort(key=lambda x: (day_order.get(x["day"], 99), time_to_minutes(x["start"])))
    
    if preference == "earliest":
        # Return earliest slot per day
        seen_days = set()
        result = []
        for slot in all_slots:
            if slot["day"] not in seen_days:
                seen_days.add(slot["day"])
                result.append(slot)
        return json.dumps(result)
    else:
        # Return all slots
        return json.dumps(result if 'result' in dir() else all_slots)
    
    return json.dumps(all_slots)
