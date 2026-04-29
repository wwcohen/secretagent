"""Auto-generated code-distilled implementation for find_available_slots."""

import json
import re
from datetime import datetime, timedelta


def find_available_slots(prompt, schedules_str):
    try:
        data = json.loads(schedules_str)
    except:
        return None
    
    participants = data.get("participants", [])
    duration = data.get("duration_minutes", 30)
    working_hours = data.get("working_hours", ["9:00", "17:00"])
    days = data.get("days", [])
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
    
    # Parse constraints from the prompt text
    # Look for patterns like "X can not meet on Day", "X would like to avoid more meetings on Day",
    # "X do not want to meet on Day", "X would rather not meet on Day"
    # Also time constraints like "before HH:MM", "after HH:MM"
    
    constraints = {}  # participant -> list of (day, type, time) constraints
    # type: 'full_day', 'before', 'after'
    
    # Extract the constraint text from the prompt (after the schedules description, before "Find a time")
    prompt_text = prompt
    
    # Parse constraints - look for sentences about participants
    # Split into sentences
    constraint_section = prompt_text
    
    # Find constraints for each participant
    for p in participants:
        constraints[p] = []
    
    # Pattern: "NAME can not meet on DAY" or "NAME do not want to meet on DAY" 
    # or "NAME would like to avoid more meetings on DAY"
    # or "NAME would rather not meet on DAY"
    # Possibly followed by time constraints like "after HH:MM" or "before HH:MM"
    # Possibly multiple days separated by periods or other punctuation
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Build a comprehensive regex to find constraints
    # We need to handle various patterns in the prompt text
    
    # First, let's extract the constraint sentences (after schedules, before "Find a time")
    find_idx = prompt_text.rfind("Find a time")
    if find_idx >= 0:
        before_find = prompt_text[:find_idx]
    else:
        before_find = prompt_text
    
    # Find the last semicolon before "Find a time" which ends the schedule descriptions
    # The constraints are between the last ";\n\n" and "Find a time"
    # Actually, constraints come after schedule descriptions
    
    # Let's find constraint text more carefully
    # Look for text after "Here are the existing schedules..." section ends
    # The schedules section ends with a line ending in "; \n\n" or similar
    
    # Split the text to get constraint lines
    lines = before_find.split('\n')
    constraint_lines = []
    found_schedules = False
    schedule_ended = False
    for line in lines:
        stripped = line.strip()
        if 'existing schedules' in stripped.lower():
            found_schedules = True
            continue
        if found_schedules and not schedule_ended:
            # Schedule lines typically contain "is busy on", "has blocked", "has meetings on", etc.
            if any(kw in stripped.lower() for kw in ['is busy', 'has blocked', 'has meetings', 'is free', 'calendar is wide open', 'no meetings']):
                continue
            elif stripped == '':
                if found_schedules:
                    schedule_ended = True
                continue
            else:
                schedule_ended = True
                constraint_lines.append(stripped)
        elif schedule_ended:
            if stripped:
                constraint_lines.append(stripped)
    
    constraint_text = ' '.join(constraint_lines)
    
    # Now parse constraints from constraint_text
    # We need to handle patterns like:
    # "Anthony can not meet on Monday. Tuesday after 14:00. Wednesday."
    # "Frances would like to avoid more meetings on Tuesday."
    # "Kenneth do not want to meet on Monday before 13:00."
    # "Benjamin can not meet on Monday after 10:30."
    # "Diana would like to avoid more meetings on Monday before 14:30."
    # "Theresa can not meet on Thursday. Emily can not meet on Monday. Tuesday."
    # "Bruce would like to avoid more meetings on Monday. Wednesday after 14:00."
    
    # Strategy: parse sentence by sentence, tracking current participant
    # Sentences are separated by periods, but day names after periods can be continuation
    
    # Split by period but keep track
    # Better approach: use regex to find constraint patterns
    
    # Pattern 1: "NAME (can not meet|do not want to meet|would rather not meet|would like to avoid more meetings) on DAYSPEC"
    # DAYSPEC can be "Day" or "Day before/after TIME" or multiple days separated by ". "
    
    # Let's tokenize the constraint text more carefully
    # Replace ". " with ".\n" for splitting, but be careful with times
    
    def parse_constraints_from_text(text):
        result = {}  # participant -> [(day, restriction_type, time_val)]
        # restriction_type: 'exclude', 'before', 'after'
        
        for p in participants:
            result[p] = []
        
        if not text.strip():
            return result
        
        # Split into sentences by ". " but handle day continuations
        # First, let's identify all constraint fragments
        # A constraint starts with a participant name and a verb phrase
        
        # Tokenize: split by sentences
        # But "Tuesday after 14:00. Wednesday." should be part of same constraint chain
        
        # Strategy: go through text, find participant + verb, then collect day specs
        
        # Patterns for constraint verbs
        verb_patterns = [
            r"can\s*not\s+meet",
            r"do\s+not\s+want\s+to\s+meet",
            r"would\s+rather\s+not\s+meet",
            r"would\s+like\s+to\s+avoid\s+more\s+meetings",
        ]
        
        # Combined pattern to find constraint starts
        name_pattern = '|'.join(re.escape(p) for p in participants)
        verb_combined = '|'.join(verb_patterns)
        
        # Find all constraint clauses
        # Pattern: (Name) (verb) on (day specs)
        pattern = rf'({name_pattern})\s+({verb_combined})\s+on\s+'
        
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        
        for i, match in enumerate(matches):
            participant_name = match.group(1)
            verb = match.group(2).lower()
            
            # Find the end of this constraint (next constraint start or end of text)
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            day_spec_text = text[start_pos:end_pos].strip()
            # Remove trailing period and "You would like..." or "The group would like..." or "Find a time..."
            # Also remove "You would like to schedule" type phrases
            
            # Split by ". " to get individual day specs, but also handle bare day names
            # e.g., "Monday. Tuesday after 14:00. Wednesday."
            # e.g., "Tuesday."
            # e.g., "Monday after 10:30."
            # e.g., "Monday before 13:00."
            # e.g., "Wednesday after 11:00. Thursday."
            
            # Clean up: remove anything that starts with "You would", "The group", "Find"
            # by finding those and truncating
            for stop_phrase in ["You would", "The group would", "Find a time", "the group would"]:
                idx = day_spec_text.find(stop_phrase)
                if idx >= 0:
                    day_spec_text = day_spec_text[:idx]
            
            # Also check for other participant names starting a new sentence (not as part of our day specs)
            for p2 in participants:
                if p2 != participant_name:
                    # Check if p2 appears and is followed by a verb pattern
                    p2_pattern = rf'{re.escape(p2)}\s+(?:{verb_combined})'
                    p2_match = re.search(p2_pattern, day_spec_text, re.IGNORECASE)
                    if p2_match:
                        day_spec_text = day_spec_text[:p2_match.start()]
            
            day_spec_text = day_spec_text.strip().rstrip('.')
            
            if not day_spec_text:
                continue
            
            # Now parse individual day specs
            # Split by ". " or "." to get individual specs
            specs = re.split(r'\.\s*', day_spec_text)
            
            for spec in specs:
                spec = spec.strip().rstrip('.')
                if not spec:
                    continue
                
                # Parse: "Day" or "Day after TIME" or "Day before TIME"
                day_match = None
                for d in day_names:
                    if spec.startswith(d):
                        day_match = d
                        remainder = spec[len(d):].strip()
                        break
                
                if not day_match:
                    continue
                
                if not remainder:
                    # Full day exclusion
                    result[participant_name].append((day_match, 'exclude', None))
                else:
                    # Parse "after TIME" or "before TIME"
                    after_match = re.match(r'after\s+(\d{1,2}:\d{2})', remainder)
                    before_match = re.match(r'before\s+(\d{1,2}:\d{2})', remainder)
                    
                    if after_match:
                        time_val = after_match.group(1)
                        result[participant_name].append((day_match, 'after', time_val))
                    elif before_match:
                        time_val = before_match.group(1)
                        result[participant_name].append((day_match, 'before', time_val))
        
        return result
    
    parsed_constraints = parse_constraints_from_text(constraint_text)
    
    # Also check for "earliest" preference from text
    # "You would like to schedule the meeting at their earlist availability"
    # "The group would like to meet at their earlist availability"
    if preference is None:
        if 'earlist availability' in constraint_text.lower() or 'earliest availability' in constraint_text.lower():
            preference = 'earliest'
        elif 'earlist' in prompt_text.lower() or 'earliest' in prompt_text.lower():
            if 'earlist availability' in prompt_text.lower() or 'earliest availability' in prompt_text.lower():
                preference = 'earliest'
    
    # Also check for "latest" preference
    if preference is None:
        if 'latest' in constraint_text.lower():
            preference = 'latest'
    
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    def get_free_intervals(busy_list, start, end):
        """Given a list of [start, end] busy intervals, return free intervals within [start, end]"""
        busy_mins = []
        for b in busy_list:
            bs = time_to_min(b[0])
            be = time_to_min(b[1])
            busy_mins.append((bs, be))
        
        # Sort busy intervals
        busy_mins.sort()
        
        # Merge overlapping
        merged = []
        for bs, be in busy_mins:
            if merged and bs <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], be))
            else:
                merged.append((bs, be))
        
        # Find free intervals
        free = []
        current = start
        for bs, be in merged:
            if bs > current:
                free.append((current, bs))
            current = max(current, be)
        if current < end:
            free.append((current, end))
        
        return free
    
    def intersect_intervals(intervals_list):
        """Intersect multiple lists of intervals"""
        if not intervals_list:
            return []
        
        result = intervals_list[0]
        for i in range(1, len(intervals_list)):
            result = intersect_two(result, intervals_list[i])
        return result
    
    def intersect_two(a, b):
        """Intersect two sorted lists of intervals"""
        result = []
        i, j = 0, 0
        while i < len(a) and j < len(b):
            start = max(a[i][0], b[j][0])
            end = min(a[i][1], b[j][1])
            if start < end:
                result.append((start, end))
            if a[i][1] < b[j][1]:
                i += 1
            else:
                j += 1
        return result
    
    def apply_constraint_to_intervals(intervals, constraint_type, time_val):
        """Apply a time constraint to intervals"""
        if constraint_type == 'exclude':
            return []
        
        tv = time_to_min(time_val)
        result = []
        
        if constraint_type == 'after':
            # Exclude times after tv -> keep only times before tv
            for s, e in intervals:
                if s < tv:
                    result.append((s, min(e, tv)))
        elif constraint_type == 'before':
            # Exclude times before tv -> keep only times at or after tv
            for s, e in intervals:
                if e > tv:
                    result.append((max(s, tv), e))
        
        return result
    
    all_slots = []
    
    for day in days:
        # Get free intervals for each participant on this day
        participant_free = []
        
        day_excluded = False
        
        for p in participants:
            p_schedule = schedules.get(p, {})
            day_schedule = p_schedule.get(day, [])
            
            free = get_free_intervals(day_schedule, work_start, work_end)
            
            # Apply constraints for this participant on this day
            if p in parsed_constraints:
                for c_day, c_type, c_time in parsed_constraints[p]:
                    if c_day == day:
                        if c_type == 'exclude':
                            free = []
                        elif c_type == 'after':
                            free = apply_constraint_to_intervals(free, 'after', c_time)
                        elif c_type == 'before':
                            free = apply_constraint_to_intervals(free, 'before', c_time)
            
            participant_free.append(free)
        
        # Intersect all participant free intervals
        common_free = intersect_intervals(participant_free)
        
        # Generate slots of exact duration
        for s, e in common_free:
            slot_start = s
            while slot_start + duration <= e:
                all_slots.append({
                    "day": day,
                    "start": min_to_time(slot_start),
                    "end": min_to_time(slot_start + duration)
                })
                slot_start += 30  # 30-minute increments
    
    # Sort by day order then by start time
    def sort_key(slot):
        d_idx = day_order.index(slot["day"]) if slot["day"] in day_order else 99
        return (d_idx, time_to_min(slot["start"]))
    
    all_slots.sort(key=sort_key)
    
    # Handle preference
    if preference == "earliest" and all_slots:
        # Return only the first slot
        return json.dumps([all_slots[0]])
    elif preference == "latest" and all_slots:
        # Return only the last slot
        return json.dumps([all_slots[-1]])
    
    # For duration > 30 (e.g., 60 min), we should return contiguous free blocks, not overlapping slots
    # Looking at expected outputs: for 60-min meetings, they return the full free intervals, not sliding windows
    # e.g., "14:00" to "15:30" is a 90-min free block returned as one slot
    # So for non-30-min durations (or actually for all), we should return the free intervals that are >= duration
    # NOT the sliding window slots
    
    # Re-examine: Looking at the expected outputs more carefully:
    # For 30-min meetings: slots are 30-min each, non-overlapping, stepping by 30 min
    # For 60-min meetings: the outputs show the FULL free intervals (not broken into 60-min chunks)
    #   e.g., "14:00" to "15:30" is returned as a single entry (90 min free)
    #   e.g., "09:00" to "10:00" is returned (exactly 60 min)
    
    # So the approach should be:
    # - Find common free intervals >= duration
    # - If duration == 30: break into 30-min slots
    # - If duration > 30: return the full free intervals (not broken into slots)
    
    # Let me re-do the slot generation
    all_slots = []
    
    for day in days:
        participant_free = []
        
        for p in participants:
            p_schedule = schedules.get(p, {})
            day_schedule = p_schedule.get(day, [])
            
            free = get_free_intervals(day_schedule, work_start, work_end)
            
            if p in parsed_constraints:
                for c_day, c_type, c_time in parsed_constraints[p]:
                    if c_day == day:
                        if c_type == 'exclude':
                            free = []
                        elif c_type == 'after':
                            free = apply_constraint_to_intervals(free, 'after', c_time)
                        elif c_type == 'before':
                            free = apply_constraint_to_intervals(free, 'before', c_time)
            
            participant_free.append(free)
        
        common_free = intersect_intervals(participant_free)
        
        if duration == 30:
            # Break into 30-min slots
            for s, e in common_free:
                slot_start = s
                while slot_start + 30 <= e:
                    all_slots.append({
                        "day": day,
                        "start": min_to_time(slot_start),
                        "end": min_to_time(slot_start + 30)
                    })
                    slot_start += 30
        else:
            # Return full free intervals that are >= duration
            for s, e in common_free:
                if e - s >= duration:
                    all_slots.append({
                        "day": day,
                        "start": min_to_time(s),
                        "end": min_to_time(e)
                    })
    
    all_slots.sort(key=sort_key)
    
    if preference == "earliest" and all_slots:
        return json.dumps([all_slots[0]])
    elif preference == "latest" and all_slots:
        return json.dumps([all_slots[-1]])
    
    return json.dumps(all_slots)
