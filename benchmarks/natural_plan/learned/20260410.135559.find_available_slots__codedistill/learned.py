"""Auto-generated code-distilled implementation for find_available_slots."""

import json
import re

def find_available_slots(prompt, schedules_str):
    try:
        data = json.loads(schedules_str)
    except:
        return None
    
    participants = data.get("participants", [])
    duration = data.get("duration_minutes", 30)
    working_hours = data.get("working_hours", ["9:00", "17:00"])
    days_list = data.get("days", [])
    preference = data.get("preference")
    schedules = data.get("schedules", {})
    
    def time_to_min(t):
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    
    def min_to_time(m):
        h = m // 60
        mi = m % 60
        return f"{h:02d}:{mi:02d}"
    
    work_start = time_to_min(working_hours[0])
    work_end = time_to_min(working_hours[1])
    
    # Parse constraints from prompt
    # Look for patterns like "X can not meet on Day", "X do not want to meet on Day",
    # "X would like to avoid more meetings on Day", "X would rather not meet on Day"
    # Also time constraints like "before HH:MM", "after HH:MM"
    
    day_exclusions = {}  # participant -> set of (day, optional_time_constraint)
    
    # Extract the constraint text (after schedules description, before "Find a time")
    constraint_text = prompt
    
    # Parse per-participant day exclusions
    # Patterns: "X can not meet on Day1. Day2." or "X do not want to meet on Day1. Day2."
    # or "X would like to avoid more meetings on Day" or "X would rather not meet on Day"
    # Also: "X can not meet on Day after/before HH:MM"
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for p in participants:
        day_exclusions[p] = []
    
    # Find constraint sentences - text between last ";\n\n" and "Find a time"
    find_idx = prompt.rfind("Find a time")
    if find_idx == -1:
        constraint_block = ""
    else:
        # Find the paragraph before "Find a time"
        schedules_end = prompt.rfind("\n\n", 0, find_idx)
        if schedules_end == -1:
            constraint_block = prompt[:find_idx]
        else:
            constraint_block = prompt[schedules_end:find_idx]
    
    # Split into sentences
    sentences = re.split(r'(?<=[.])\s*', constraint_block.strip())
    
    # For each participant, find their constraints
    for p in participants:
        # Find sentences mentioning this participant
        p_escaped = re.escape(p)
        
        # Pattern: "P can not meet on Day1. Day2." or "P do not want to meet on Day1. Day2. Day3."
        # These often span multiple sentences where subsequent ones are just day names
        
        # Find all relevant patterns
        patterns = [
            rf'{p_escaped}\s+(?:can\s*not|cannot|do\s*not\s*want\s*to|would\s*(?:like\s*to\s*avoid\s*more\s*meetings|rather\s*not\s*meet|prefer\s*not\s*to\s*meet))\s+on\s+(.*?)(?=\.\s*(?:You|The\s+group|Find|[A-Z][a-z]+\s+(?:can|do|would|has|is|prefer))|\.\s*$)',
        ]
        
        # More flexible: just find the text after "on" for this participant
        match = re.search(
            rf'{p_escaped}\s+(?:can\s*not|cannot|do\s*not\s*want\s*to|would\s+like\s+to\s+avoid\s+more\s+meetings\s+on|would\s+rather\s+not\s+meet\s+on|prefer(?:s)?\s+not\s+to\s+meet\s+on)\s*(.*?)(?=\.\s*(?:You|The\s+group|Find)|$)',
            constraint_block, re.DOTALL
        )
        
        if not match:
            match = re.search(
                rf'{p_escaped}\s+(?:can\s*not\s*meet\s*on|do\s*not\s*want\s*to\s*meet\s*on|would\s+like\s+to\s+avoid\s+more\s+meetings\s+on|would\s+rather\s+not\s+meet\s+on)\s*(.*?)(?=\.\s*(?:You|The\s+group|Find|[A-Z][a-z]+\s+(?:can|do|would|has|is)))',
                constraint_block, re.DOTALL
            )
        
        if not match:
            # Try even broader
            match = re.search(
                rf'{p_escaped}\s+(?:can\s*not\s*meet|do\s*not\s*want\s*to\s*meet|would\s+like\s+to\s+avoid\s+more\s+meetings|would\s+rather\s+not\s+meet)\s+on\s+(.*?)(?:\.\s*(?:You|The\s+group|Find|[A-Z][a-z]+\s+(?:can|do|would|has|is)))',
                constraint_block, re.DOTALL
            )
        
        if match:
            rest = match.group(1).strip().rstrip('.')
            # Parse day constraints from this text
            # Could be like "Monday. Tuesday" or "Monday after 10:30" or "Monday. Tuesday after 14:00. Wednesday"
            # Split by ". " or "." to get individual day constraints
            parts = re.split(r'\.\s*', rest)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                # Check if it's just a day name
                for d in day_names:
                    if d in part:
                        time_match = re.search(rf'{d}\s+(before|after)\s+(\d{{1,2}}:\d{{2}})', part)
                        if time_match:
                            direction = time_match.group(1)
                            t = time_match.group(2)
                            day_exclusions[p].append((d, direction, time_to_min(t)))
                        else:
                            day_exclusions[p].append((d, 'all', None))
                        break
                else:
                    # Maybe it's just a day name without prefix
                    stripped = part.strip()
                    for d in day_names:
                        if stripped.startswith(d):
                            time_match = re.search(rf'(before|after)\s+(\d{{1,2}}:\d{{2}})', stripped)
                            if time_match:
                                direction = time_match.group(1)
                                t = time_match.group(2)
                                day_exclusions[p].append((d, direction, time_to_min(t)))
                            else:
                                day_exclusions[p].append((d, 'all', None))
                            break
    
    # Also check for "You would like to schedule the meeting at their earliest availability"
    # This is handled by the preference field
    
    def get_free_intervals(busy_list, start, end):
        """Given busy intervals and a range, return free intervals."""
        busy = []
        for b in busy_list:
            bs = time_to_min(b[0])
            be = time_to_min(b[1])
            busy.append((bs, be))
        busy.sort()
        
        # Merge overlapping busy intervals
        merged = []
        for bs, be in busy:
            if merged and bs <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], be))
            else:
                merged.append((bs, be))
        
        free = []
        current = start
        for bs, be in merged:
            if current < bs:
                free.append((current, bs))
            current = max(current, be)
        if current < end:
            free.append((current, end))
        
        return free
    
    def intersect_intervals(list1, list2):
        """Intersect two lists of intervals."""
        result = []
        i, j = 0, 0
        while i < len(list1) and j < len(list2):
            s1, e1 = list1[i]
            s2, e2 = list2[j]
            start = max(s1, s2)
            end = min(e1, e2)
            if start < end:
                result.append((start, end))
            if e1 < e2:
                i += 1
            else:
                j += 1
        return result
    
    def apply_exclusions(intervals, participant, day):
        """Apply participant exclusions to intervals for a given day."""
        if participant not in day_exclusions:
            return intervals
        
        result = intervals
        for exc in day_exclusions[participant]:
            d, direction, t = exc
            if d != day:
                continue
            if direction == 'all':
                return []
            elif direction == 'before':
                # Exclude times before t
                new_result = []
                for s, e in result:
                    if e <= t:
                        continue
                    elif s >= t:
                        new_result.append((s, e))
                    else:
                        new_result.append((t, e))
                result = new_result
            elif direction == 'after':
                # Exclude times after t
                new_result = []
                for s, e in result:
                    if s >= t:
                        continue
                    elif e <= t:
                        new_result.append((s, e))
                    else:
                        new_result.append((s, t))
                result = new_result
        return result
    
    all_slots = []
    
    for day in days_list:
        # Compute free intervals for each participant on this day
        common_free = [(work_start, work_end)]
        
        for p in participants:
            p_schedule = schedules.get(p, {})
            day_schedule = p_schedule.get(day, [])
            
            p_free = get_free_intervals(day_schedule, work_start, work_end)
            
            # Apply exclusions for this participant on this day
            p_free = apply_exclusions(p_free, p, day)
            
            common_free = intersect_intervals(common_free, p_free)
        
        # Now split common_free into duration-sized blocks
        for s, e in common_free:
            if e - s >= duration:
                # Generate all duration-sized blocks
                t = s
                while t + duration <= e:
                    all_slots.append({"day": day, "start": min_to_time(t), "end": min_to_time(t + duration)})
                    t += duration
    
    if preference == "earliest" and all_slots:
        # Return only the first slot
        return json.dumps([all_slots[0]])
    
    if not all_slots:
        return json.dumps([])
    
    return json.dumps(all_slots)
