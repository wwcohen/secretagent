"""Auto-generated code-distilled implementation for find_available_slots."""

import json
import re

def find_available_slots(prompt, schedules_json):
    data = json.loads(schedules_json)
    participants = data["participants"]
    duration = data["duration_minutes"]
    wh = data["working_hours"]
    days = data["days"]
    preference = data.get("preference")
    schedules = data["schedules"]
    
    def time_to_min(t):
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    
    def min_to_time(m):
        return f"{m // 60:02d}:{m % 60:02d}"
    
    wh_start = time_to_min(wh[0])
    wh_end = time_to_min(wh[1])
    
    # Parse text constraints from prompt
    day_exclusions = {}  # participant -> {day: [(start, end)] or 'exclude'}
    prompt_lower = prompt.lower()
    
    # Pattern: "X do not want to meet on Day" or "X would rather not meet on Day"
    # or "X can not meet on Day before/after HH:MM"
    for p in participants:
        pl = p.lower()
        # "do not want to meet on Monday" -> exclude that day
        for day in days:
            dl = day.lower()
            pat1 = re.search(rf'{pl}\s+(?:do not want to meet|would rather not meet|can not meet|cannot meet)\s+on\s+{dl}\b([^.]*)', prompt_lower)
            if pat1:
                rest = pat1.group(1).strip()
                if not rest:
                    day_exclusions.setdefault(p, {})[day] = 'exclude'
                else:
                    after_match = re.search(r'after\s+(\d+:\d+)', rest)
                    before_match = re.search(r'before\s+(\d+:\d+)', rest)
                    if after_match:
                        t = time_to_min(after_match.group(1))
                        day_exclusions.setdefault(p, {}).setdefault(day, []).append(('after', t))
                    if before_match:
                        t = time_to_min(before_match.group(1))
                        day_exclusions.setdefault(p, {}).setdefault(day, []).append(('before', t))
    
    all_slots = []
    
    for day in days:
        # Collect all busy intervals
        busy = []
        skip_day = False
        for p in participants:
            if p in day_exclusions:
                if day in day_exclusions[p]:
                    val = day_exclusions[p][day]
                    if val == 'exclude':
                        skip_day = True
                        break
            if day in schedules.get(p, {}):
                for interval in schedules[p][day]:
                    s = time_to_min(interval[0])
                    e = time_to_min(interval[1])
                    busy.append((s, e))
        
        if skip_day:
            continue
        
        # Add constraint-based busy times
        for p in participants:
            if p in day_exclusions and day in day_exclusions[p]:
                val = day_exclusions[p][day]
                if isinstance(val, list):
                    for constraint_type, t in val:
                        if constraint_type == 'after':
                            busy.append((t, wh_end))
                        elif constraint_type == 'before':
                            busy.append((wh_start, t))
        
        busy.sort()
        # Merge busy intervals
        merged = []
        for s, e in busy:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        
        # Find free slots
        free_start = wh_start
        for s, e in merged:
            if s > free_start and s - free_start >= duration:
                # Generate duration-sized slots
                t = free_start
                while t + duration <= s:
                    all_slots.append({"day": day, "start": min_to_time(t), "end": min_to_time(t + duration)})
                    t += duration
            free_start = max(free_start, e)
        if wh_end > free_start and wh_end - free_start >= duration:
            t = free_start
            while t + duration <= wh_end:
                all_slots.append({"day": day, "start": min_to_time(t), "end": min_to_time(t + duration)})
                t += duration
    
    if preference == "earliest":
        # Return earliest slot per day (one per day that has a slot)
        seen_days = set()
        result = []
        for slot in all_slots:
            if slot["day"] not in seen_days:
                seen_days.add(slot["day"])
                result.append(slot)
        return json.dumps(result)
    else:
        return json.dumps(all_slots)
