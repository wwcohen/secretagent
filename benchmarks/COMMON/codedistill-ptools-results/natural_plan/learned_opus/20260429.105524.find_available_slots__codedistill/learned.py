"""Auto-generated code-distilled implementation for find_available_slots."""

import json
import re

def find_available_slots(problem_text, schedules_json):
    try:
        data = json.loads(schedules_json)
    except:
        return None
    
    participants = data["participants"]
    duration = data["duration_minutes"]
    wh_start_str, wh_end_str = data["working_hours"]
    days = data["days"]
    preference = data.get("preference")
    schedules = data["schedules"]
    
    def time_to_min(t):
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    
    def min_to_time(m):
        h = m // 60
        mn = m % 60
        return f"{h:02d}:{mn:02d}"
    
    wh_start = time_to_min(wh_start_str)
    wh_end = time_to_min(wh_end_str)
    
    # Parse constraints from problem_text
    # Look for patterns like:
    # "X can not meet on DAY before TIME"
    # "X can not meet on DAY after TIME"
    # "X do not want to meet on DAY before TIME"
    # "X do not want to meet on DAY after TIME"
    # "X would like to avoid more meetings on DAY before TIME"
    # "X would like to avoid more meetings on DAY after TIME"
    # "X do not want to meet on DAY" (whole day)
    # "X can not meet on DAY" (whole day)
    # "X would rather not meet on DAY after TIME"
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Constraints: list of (person, day_or_None, constraint_type, time_or_None)
    # constraint_type: 'no_day', 'no_before', 'no_after'
    constraints = []
    
    # Pattern: "NAME can not meet on DAY before TIME"
    # Pattern: "NAME can not meet on DAY after TIME"  
    # Pattern: "NAME can not meet on DAY" (whole day exclusion)
    # Pattern: "NAME do not want to meet on DAY before TIME"
    # Pattern: "NAME do not want to meet on DAY after TIME"
    # Pattern: "NAME do not want to meet on DAY" (whole day)
    # Pattern: "NAME would like to avoid more meetings on DAY before TIME"
    # Pattern: "NAME would like to avoid more meetings on DAY after TIME"
    # Pattern: "NAME would rather not meet on DAY after TIME"
    # Pattern: "NAME would rather not meet on DAY before TIME"
    
    day_pattern = "|".join(day_names)
    time_pattern = r'\d{1,2}:\d{2}'
    
    # Build name pattern from participants
    name_pattern = "|".join(re.escape(p) for p in participants)
    
    # Match "NAME ... not meet on DAY before/after TIME"
    # and "NAME ... avoid ... on DAY before/after TIME"
    # and "NAME ... not meet on DAY" (no before/after)
    
    text = problem_text
    
    # Pattern 1: cannot/don't want to meet on DAY before/after TIME
    patterns_with_time = [
        rf'({name_pattern})\s+(?:can\s*not|cannot|do\s+not\s+want\s+to|would\s+like\s+to\s+avoid\s+(?:more\s+)?meetings?\s+on|would\s+rather\s+not)\s+meet\s+on\s+({day_pattern})\s+(before|after)\s+({time_pattern})',
        rf'({name_pattern})\s+(?:can\s*not|cannot|do\s+not\s+want\s+to|would\s+like\s+to\s+avoid\s+(?:more\s+)?meetings?\s+on|would\s+rather\s+not)\s+meet\s+(?:on\s+)?({day_pattern})\s+(before|after)\s+({time_pattern})',
        rf'({name_pattern})\s+(?:would\s+like\s+to\s+avoid\s+more\s+meetings\s+on)\s+({day_pattern})\s+(before|after)\s+({time_pattern})',
        rf'({name_pattern})\s+(?:would\s+rather\s+not\s+meet\s+on)\s+({day_pattern})\s+(before|after)\s+({time_pattern})',
    ]
    
    for pat in patterns_with_time:
        for m in re.finditer(pat, text, re.IGNORECASE):
            name = m.group(1)
            day = m.group(2)
            direction = m.group(3).lower()
            time_val = m.group(4)
            if direction == "before":
                constraints.append((name, day, 'no_before', time_to_min(time_val)))
            else:
                constraints.append((name, day, 'no_after', time_to_min(time_val)))
    
    # Pattern 2: cannot/don't want to meet on DAY (whole day exclusion, no before/after)
    patterns_whole_day = [
        rf'({name_pattern})\s+(?:can\s*not|cannot|do\s+not\s+want\s+to)\s+meet\s+on\s+({day_pattern})(?:\s*\.|\s*;|\s*,|\s+[A-Z])',
        rf'({name_pattern})\s+(?:would\s+like\s+to\s+avoid\s+more\s+meetings\s+on)\s+({day_pattern})(?:\s*\.|\s*;|\s*,|\s+[A-Z])',
        rf'({name_pattern})\s+(?:would\s+rather\s+not\s+meet\s+on)\s+({day_pattern})(?:\s*\.|\s*;|\s*,|\s+[A-Z])',
    ]
    
    for pat in patterns_whole_day:
        for m in re.finditer(pat, text, re.IGNORECASE):
            name = m.group(1)
            day = m.group(2)
            # Check it's not followed by before/after (already captured above)
            end_pos = m.end(2)
            remaining = text[end_pos:end_pos+30].strip()
            if remaining and (remaining.startswith("before") or remaining.startswith("after")):
                continue
            constraints.append((name, day, 'no_day', None))
    
    # Also check for "X do not want to meet on DAY." at end
    patterns_whole_day2 = [
        rf'({name_pattern})\s+(?:can\s*not|cannot)\s+meet\s+on\s+({day_pattern})\b',
        rf'({name_pattern})\s+(?:do\s+not\s+want\s+to)\s+meet\s+on\s+({day_pattern})\b',
        rf'({name_pattern})\s+(?:would\s+like\s+to\s+avoid\s+(?:more\s+)?meetings?\s+on)\s+({day_pattern})\b',
        rf'({name_pattern})\s+(?:would\s+rather\s+not\s+meet\s+on)\s+({day_pattern})\b',
    ]
    
    # Re-check whole day patterns more carefully
    constraints_whole_day = []
    for pat in patterns_whole_day2:
        for m in re.finditer(pat, text, re.IGNORECASE):
            name = m.group(1)
            day = m.group(2)
            end_pos = m.end()
            remaining = text[end_pos:end_pos+30].strip()
            if remaining.startswith("before") or remaining.startswith("after"):
                continue
            constraints_whole_day.append((name, day, 'no_day', None))
    
    # Merge constraints (avoid duplicates)
    all_constraints = constraints + constraints_whole_day
    seen = set()
    unique_constraints = []
    for c in all_constraints:
        key = (c[0], c[1], c[2], c[3])
        if key not in seen:
            seen.add(key)
            unique_constraints.append(c)
    constraints = unique_constraints
    
    results = []
    
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    sorted_days = sorted(days, key=lambda d: day_order.index(d) if d in day_order else 99)
    
    for day in sorted_days:
        # Check if any participant has a whole-day exclusion for this day
        day_excluded_participants = set()
        for (name, cday, ctype, ctime) in constraints:
            if ctype == 'no_day' and cday == day:
                day_excluded_participants.add(name)
        
        # If any participant can't meet this day at all, skip
        if day_excluded_participants:
            # Actually, need to think: if participant can't meet on this day, skip the whole day
            # But wait - some examples show we still skip the day
            # Let's skip the day entirely if any participant has no_day constraint
            continue
        
        # Collect all busy intervals for this day
        all_busy = []
        
        for p in participants:
            if p in schedules and day in schedules[p]:
                for slot in schedules[p][day]:
                    s = time_to_min(slot[0])
                    e = time_to_min(slot[1])
                    all_busy.append((s, e))
        
        # Add constraints as busy intervals
        for (name, cday, ctype, ctime) in constraints:
            if cday == day and name in participants:
                if ctype == 'no_before':
                    # Can't meet before ctime -> block from wh_start to ctime
                    all_busy.append((wh_start, ctime))
                elif ctype == 'no_after':
                    # Can't meet after ctime -> block from ctime to wh_end
                    all_busy.append((ctime, wh_end))
        
        # Merge busy intervals
        if all_busy:
            all_busy.sort()
            merged = [all_busy[0]]
            for s, e in all_busy[1:]:
                if s <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], e))
                else:
                    merged.append((s, e))
        else:
            merged = []
        
        # Find free slots
        free_slots = []
        current = wh_start
        for s, e in merged:
            if s > current:
                free_slots.append((current, s))
            current = max(current, e)
        if current < wh_end:
            free_slots.append((current, wh_end))
        
        # Break free slots into duration-sized chunks
        day_slots = []
        for fs, fe in free_slots:
            slot_start = fs
            while slot_start + duration <= fe:
                day_slots.append({
                    "day": day,
                    "start": min_to_time(slot_start),
                    "end": min_to_time(slot_start + duration)
                })
                slot_start += 30  # increment by 30 min steps
        
        if preference == "earliest" and day_slots:
            # Return only the earliest slot for this day? 
            # Looking at examples more carefully:
            # When preference is "earliest", for multi-day cases we get one slot per day
            # Actually looking at example 4 (Christine/Jose, earliest): returns one slot per day
            # Example 10 (Raymond/Gerald, earliest): returns multiple slots on Monday
            # Wait, example 10 has 2 Monday slots...
            # Actually re-reading: preference "earliest" seems to just mean 
            # return earliest slot overall? But example 4 returns slots across days...
            # Let me look again: example 2 (earliest) -> 1 slot
            # example 4 (earliest) -> 1 per day (3 days, 3 slots)  
            # example 10 (earliest) -> 2 Monday slots
            # example 16 (earliest) -> 1 slot
            # Hmm, example 10 expected: Monday 10:30-11:00 and Monday 15:00-15:30
            # That's 2 slots on same day. So "earliest" doesn't mean "one per day"
            # 
            # Wait - in example 10, Raymond wants to avoid Tuesday meetings.
            # So Tuesday is excluded entirely. The only slots are on Monday.
            # And there are exactly 2 free slots on Monday. So all are returned.
            #
            # In example 4 (earliest), there's 1 slot per day returned, but
            # let me check if there really is only 1 available slot per day...
            # Christine/Jose Monday: busy merge... yes probably 1 per day.
            #
            # So "earliest" might just mean return all available slots 
            # (same as null preference). The preference is for the LLM prompt,
            # not for filtering.
            
            results.extend(day_slots)
        else:
            results.extend(day_slots)
    
    return json.dumps(results)
