"""Auto-generated workflow-distilled implementation for calendar_scheduling.

Calls existing tools from ptools_calendar.
"""

from ptools_calendar import *

import re

def calendar_scheduling(prompt: str) -> str:
    text = prompt
    
    # Extract meeting duration
    if 'one hour' in text or '1 hour' in text:
        duration = 60
    elif 'half an hour' in text or '30 minutes' in text:
        duration = 30
    elif 'two hours' in text or '2 hours' in text:
        duration = 120
    elif 'one and a half hours' in text or '1.5 hours' in text or '90 minutes' in text:
        duration = 90
    else:
        # Try to extract minutes
        m = re.search(r'(\d+)\s*minutes?', text)
        if m:
            duration = int(m.group(1))
        else:
            duration = 30
    
    # Extract days
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Check which days are available from the TASK line
    task_match = re.search(r'TASK:.*?SOLUTION:', text, re.DOTALL)
    task_text = task_match.group(0) if task_match else text
    
    available_days = []
    # Look for "on either Monday, Tuesday, ..." or "on Monday"
    day_pattern = re.search(r'on(?:\s+either)?\s+((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:(?:\s*,\s*|\s+or\s+|\s+and\s+)(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))*)', task_text)
    if day_pattern:
        day_str = day_pattern.group(1)
        for d in days_order:
            if d in day_str:
                available_days.append(d)
    
    if not available_days:
        available_days = ['Monday']
    
    # Extract work hours
    work_match = re.search(r'work hours of (\d{1,2}:\d{2}) to (\d{1,2}:\d{2})', text)
    if work_match:
        work_start = time_to_min(work_match.group(1))
        work_end = time_to_min(work_match.group(2))
    else:
        work_start = time_to_min('9:00')
        work_end = time_to_min('17:00')
    
    # Extract participants' schedules
    # Find the schedules section
    schedules_section = text[text.find('Here are the existing schedules'):]
    # Cut at the preferences/constraints or SOLUTION
    sol_idx = schedules_section.find('SOLUTION:')
    if sol_idx != -1:
        schedules_section = schedules_section[:sol_idx]
    
    # Parse each person's busy times per day
    # Build a dict: day -> list of (start_min, end_min) busy intervals
    busy_by_day = {d: [] for d in days_order}
    
    # Parse lines like:
    # "Name has meetings on Monday during 10:00 to 11:00, 12:00 to 12:30, Tuesday during ..."
    # "Name is busy on Monday during ..."
    # "Name has blocked their calendar on Monday during ..."
    # "Name is free the entire day."
    # "Name has no meetings the whole day."
    
    # Split by participant schedules - find all schedule descriptions
    # Each starts with a name and describes their schedule
    schedule_lines = re.split(r'\n', schedules_section)
    
    # Actually, let's parse more carefully by finding each person's schedule entry
    # They can span descriptions like "Name has meetings on Monday during X, Tuesday during Y;"
    
    # Combine all lines into one block
    block = ' '.join(schedules_section.split())
    
    # Find all schedule entries - each starts with a capitalized name
    # Pattern: Name (is busy|has meetings|has blocked|is free|has no meetings)
    entries = re.findall(
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:is busy|has meetings|has blocked their calendar|is free|has no meetings|\'s calendar is wide open).*?(?=(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*(?:is busy|has meetings|has blocked|is free|has no meetings|\'s calendar|can not|would|do not|prefers))|(?:Find a time)|(?:The group)|(?:SOLUTION)|$)',
        block
    )
    
    # Better approach: parse the whole text for busy intervals
    # Find all patterns like "on Monday during 10:00 to 11:00"
    
    # Let me use a more robust parsing approach
    # First, extract all busy time intervals per day from the schedules section
    
    # Find the text between "Here are the existing schedules" and preferences/Find a time
    sched_end_patterns = [
        'Find a time that works',
        'The group would like',
    ]
    
    # Also look for preference lines that come after schedules
    pref_patterns_starts = [
        r'[A-Z][a-z]+ would like to avoid',
        r'[A-Z][a-z]+ would rather not',
        r'[A-Z][a-z]+ can not meet',
        r'[A-Z][a-z]+ do not want',
        r'[A-Z][a-z]+ prefers',
        r'[A-Z][a-z]+ would prefer',
        r'The group would like',
    ]
    
    # Get schedules text and preferences text
    find_time_idx = text.find('Find a time that works')
    if find_time_idx == -1:
        find_time_idx = text.find('SOLUTION:')
    
    sched_start_idx = text.find('Here are the existing schedules')
    if sched_start_idx == -1:
        sched_start_idx = 0
    
    sched_text = text[sched_start_idx:find_time_idx]
    
    # Also get preference text (between schedules and "Find a time")
    # Preferences might be after the schedule entries but before "Find a time"
    pref_text = text[sched_start_idx:find_time_idx + 100] if find_time_idx != -1 else ''
    
    # Parse busy times from sched_text
    # Strategy: for each day mentioned with "during", extract all time ranges
    
    # First parse per-person schedules
    # Each person's entry ends with ";\n" or ".\n" typically
    
    # Let's find all busy intervals globally per day
    # Pattern: DayName during time_range(, time_range)*
    
    def parse_all_busy(txt):
        """Parse all busy intervals from text, return dict day -> list of (start, end) in minutes"""
        result = {d: [] for d in days_order}
        
        # Find all occurrences of "DayName during TIME to TIME(, TIME to TIME)*"
        for day in days_order:
            # Find all "day during ..." segments
            pattern = day + r'\s+during\s+([\d:]+\s+to\s+[\d:]+(?:\s*,\s*[\d:]+\s+to\s+[\d:]+)*)'
            matches = re.findall(pattern, txt)
            for match in matches:
                # Extract individual time ranges
                ranges = re.findall(r'(\d{1,2}:\d{2})\s+to\s+(\d{1,2}:\d{2})', match)
                for start_str, end_str in ranges:
                    result[day].append((time_to_min(start_str), time_to_min(end_str)))
        
        return result
    
    busy_by_day = parse_all_busy(sched_text)
    
    # Parse preferences
    # Types of preferences:
    # 1. "Name would like to avoid more meetings on Day before/after HH:MM"
    # 2. "Name would rather not meet on Day"
    # 3. "Name can not meet on Day"
    # 4. "Name do not want to meet on Day"
    # 5. "Name can not meet on Day before/after HH:MM"
    # 6. "The group would like to meet at their earliest availability"
    # 7. "Name would like to avoid more meetings on Day before HH:MM"
    
    prefer_earliest = False
    prefer_latest = False
    
    # Additional blocked intervals from preferences
    pref_blocked = {d: [] for d in days_order}
    
    # Get the text after schedules but before SOLUTION
    sol_idx2 = text.find('SOLUTION:')
    after_sched = text[text.rfind(';', 0, find_time_idx) + 1:sol_idx2] if find_time_idx != -1 else ''
    if not after_sched.strip():
        after_sched = text[sched_start_idx:sol_idx2]
    
    # Check for earliest/latest preference
    if 'earlist availability' in text or 'earliest availability' in text:
        prefer_earliest = True
    if 'latest availability' in text or 'as late as possible' in text:
        prefer_latest = True
    
    # Parse constraint sentences between the last ";" of schedules and "Find a time"
    constraint_text = ''
    if find_time_idx != -1:
        # Find the last schedule entry end before "Find a time"
        # Schedule entries end with "; \n" typically
        # Look for text between last ";\n" and "Find a time"
        before_find = text[:find_time_idx]
        # Find all newlines
        last_semicolon = before_find.rfind(';')
        last_period = before_find.rfind('.')
        # The constraints are typically on lines after the schedule entries
        # Let's get everything between the schedule block and "Find a time"
        
        # Find where schedule entries end
        # Schedule entries contain "during" keyword
        lines = before_find.split('\n')
        constraint_lines = []
        past_schedules = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if 'Here are the existing schedules' in stripped:
                past_schedules = False
                continue
            if past_schedules:
                # Check if this is still a schedule line
                if 'during' in stripped or 'is free' in stripped or 'no meetings' in stripped or 'wide open' in stripped:
                    continue
                else:
                    constraint_lines.append(stripped)
            if 'during' in stripped or 'is free' in stripped or 'no meetings' in stripped or 'wide open' in stripped:
                past_schedules = True
        
        constraint_text = ' '.join(constraint_lines)
    
    # Also look for constraints in the text right before "Find a time"
    if find_time_idx != -1:
        # Get up to 500 chars before "Find a time"
        pre_find = text[max(0, find_time_idx - 500):find_time_idx].strip()
        # Split by newlines and get lines that don't have "during" patterns (not schedule lines)
        ct_lines = pre_find.split('\n')
        for line in ct_lines:
            s = line.strip()
            if not s:
                continue
            # Skip schedule lines
            if any(kw in s.lower() for kw in ['during', 'is free', 'no meetings', 'wide open', 'here are the existing']):
                continue
            if s not in constraint_text:
                constraint_text += ' ' + s
    
    # Parse day-level blocks from constraints
    # "Name can not meet on Day." -> block entire day
    # "Name would rather not meet on Day." -> block entire day (soft preference but treated as constraint)
    # "Name do not want to meet on Day." -> block entire day
    # "Name can not meet on Day before HH:MM" -> block day before time
    # "Name can not meet on Day after HH:MM" -> block day after time
    # "Name would like to avoid more meetings on Day before HH:MM" -> block day before time
    
    # Parse the constraint text
    # Split on periods and process each sentence
    constraint_sentences = re.split(r'(?<=[.])\s*', constraint_text)
    
    # Also try splitting by sentence boundaries more carefully
    # Sometimes constraints are separated by periods within one paragraph
    all_constraints_text = constraint_text
    
    # Handle patterns like "Name can not meet on Monday. Tuesday." meaning both days blocked
    # And "Name can not meet on Monday before 10:00. Tuesday after 14:00."
    
    def parse_constraints(ctext):
        """Parse constraint text and return additional blocked intervals per day"""
        blocks = {d: [] for d in days_order}
        
        if not ctext.strip():
            return blocks
        
        # Normalize
        ctext = ctext.replace('\n', ' ').strip()
        
        # Split into individual constraint statements
        # Each typically starts with a name
        # Pattern: "Name (can not|would rather not|do not want|would like to avoid) ..."
        
        # Find all constraint clauses
        # Handle compound sentences like "Gerald do not want to meet on Monday. Tuesday."
        # This means Gerald doesn't want Monday or Tuesday
        
        # Strategy: find each person's constraint block
        # A person's constraints start with their name and a constraint verb
        # The constraint may span multiple sentences referencing days
        
        constraint_verbs = [
            'can not meet',
            'cannot meet', 
            'would rather not meet',
            'do not want to meet',
            'does not want to meet',
            'would like to avoid more meetings',
            'would like to avoid meetings',
            'prefers not to meet',
            'would prefer not to meet',
        ]
        
        # Find each person's constraint segment
        # Split by person name + constraint verb
        segments = []
        pattern_parts = []
        for verb in constraint_verbs:
            pattern_parts.append(verb)
        
        verb_pattern = '|'.join(re.escape(v) for v in constraint_verbs)
        # Match: Name verb_phrase ...until next Name verb_phrase or end
        seg_pattern = r'([A-Z][a-z]+)\s+(?:' + verb_pattern + r')\s+(.*?)(?=(?:[A-Z][a-z]+\s+(?:' + verb_pattern + r'))|Find a time|$)'
        
        seg_matches = re.finditer(seg_pattern, ctext, re.DOTALL)
        
        for sm in seg_matches:
            name = sm.group(1)
            details = sm.group(2).strip()
            
            # Parse the details for day blocks
            # Examples:
            # "on Monday."
            # "on Monday. Tuesday."
            # "on Monday before 10:00."
            # "on Monday. Tuesday after 14:00."
            # "on Wednesday after 11:30."
            # "on Monday before 14:30."
            
            # Remove "on " prefix
            details = re.sub(r'^on\s+', '', details)
            
            # Split by day references
            # Each segment is either "DayName" or "DayName before/after TIME"
            # Separated by ". " or ", "
            
            # Tokenize by splitting on periods and commas
            parts = re.split(r'[.]\s*', details)
            
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                
                # Remove leading "on "
                part = re.sub(r'^on\s+', '', part)
                
                for day in days_order:
                    if part.startswith(day):
                        rest = part[len(day):].strip()
                        
                        if not rest:
                            # Block entire day
                            blocks[day].append((work_start, work_end))
                        elif rest.startswith('before'):
                            time_match = re.search(r'before\s+(\d{1,2}:\d{2})', rest)
                            if time_match:
                                t = time_to_min(time_match.group(1))
                                blocks[day].append((work_start, t))
                        elif rest.startswith('after'):
                            time_match = re.search(r'after\s+(\d{1,2}:\d{2})', rest)
                            if time_match:
                                t = time_to_min(time_match.group(1))
                                blocks[day].append((t, work_end))
                        break
        
        return blocks
    
    # Also check "The group would like to meet at their earlist availability"
    if 'earlist' in text or 'earliest' in text:
        prefer_earliest = True
    if 'latest' in text:
        prefer_latest = True
    
    pref_blocked = parse_constraints(all_constraints_text)
    
    # Merge busy intervals and preference blocks
    for day in days_order:
        busy_by_day[day] = busy_by_day.get(day, []) + pref_blocked.get(day, [])
    
    # Now find available slots
    def find_free_slots(day):
        """Find free intervals on a given day"""
        busy = sorted(busy_by_day.get(day, []))
        if not busy:
            return [(work_start, work_end)]
        
        # Merge overlapping intervals
        merged = []
        for start, end in busy:
            # Clip to work hours
            start = max(start, work_start)
            end = min(end, work_end)
            if start >= end:
                continue
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        # Find gaps
        free = []
        prev_end = work_start
        for start, end in merged:
            if start > prev_end:
                free.append((prev_end, start))
            prev_end = max(prev_end, end)
        if prev_end < work_end:
            free.append((prev_end, work_end))
        
        return free
    
    # Find the first/best slot
    best_slot = None
    
    if prefer_latest:
        # Search days in reverse, and within each day search from latest
        for day in reversed(available_days):
            free = find_free_slots(day)
            # Search from latest free slot
            for start, end in reversed(free):
                if end - start >= duration:
                    # Take the latest possible slot in this interval
                    slot_start = end - duration
                    slot_end = end
                    best_slot = (day, slot_start, slot_end)
                    break
            if best_slot:
                break
    else:
        # Default: earliest (either explicit or implicit)
        for day in available_days:
            free = find_free_slots(day)
            for start, end in free:
                if end - start >= duration:
                    slot_start = start
                    slot_end = start + duration
                    best_slot = (day, slot_start, slot_end)
                    break
            if best_slot:
                break
    
    if best_slot:
        day, start, end = best_slot
        return f'Here is the proposed time: {day}, {min_to_time(start)} - {min_to_time(end)} '
    
    # Fallback: try the LLM-based approach
    return calendar_workflow(prompt)


def time_to_min(t: str) -> int:
    """Convert HH:MM string to minutes since midnight"""
    parts = t.strip().split(':')
    return int(parts[0]) * 60 + int(parts[1])


def min_to_time(m: int) -> str:
    """Convert minutes since midnight to HH:MM string"""
    h = m // 60
    mins = m % 60
    return f'{h}:{mins:02d}'
