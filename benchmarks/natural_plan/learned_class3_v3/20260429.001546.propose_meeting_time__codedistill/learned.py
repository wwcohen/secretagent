"""Auto-generated code-distilled implementation for propose_meeting_time."""

import re

def propose_meeting_time(text):
    if text is None:
        return None
    
    # Simple case: just "Day HH:MM-HH:MM"
    simple_match = re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$', text.strip())
    if simple_match:
        day = simple_match.group(1)
        start = simple_match.group(2)
        end = simple_match.group(3)
        start = format_time_str(start)
        end = format_time_str(end)
        return f'Here is the proposed time: {day}, {start} - {end}'
    
    # Parse duration
    duration = parse_duration(text)
    if duration is None:
        duration = 30  # default
    
    # Parse time window
    window_start, window_end = parse_time_window(text)
    
    # Parse available days
    days = parse_days(text)
    
    # Parse participants and their busy times
    busy_times = parse_busy_times(text, days)
    
    # Parse preferences (day avoidance, time constraints)
    day_prefs, time_constraints = parse_preferences(text)
    
    # Order days: preferred days first (days not avoided), then avoided days
    avoided_days = set()
    for person, avoided in day_prefs.items():
        for d in avoided:
            avoided_days.add(d)
    
    preferred_days = [d for d in days if d not in avoided_days]
    non_preferred_days = [d for d in days if d in avoided_days]
    ordered_days = preferred_days + non_preferred_days
    
    # For each day, find earliest slot
    for day in ordered_days:
        # Collect all busy intervals for this day
        all_busy = []
        for person, day_busy in busy_times.items():
            if day in day_busy:
                all_busy.extend(day_busy[day])
        
        # Apply time constraints per person
        for person, constraints in time_constraints.items():
            for constraint in constraints:
                ctype, ctime = constraint
                if ctype == 'not_after':
                    # Person doesn't want to meet after ctime
                    # So block from ctime to window_end
                    all_busy.append((ctime, window_end))
                elif ctype == 'not_before':
                    # Block from window_start to ctime
                    all_busy.append((window_start, ctime))
        
        # Merge busy intervals
        merged = merge_intervals(all_busy)
        
        # Find earliest free slot of required duration
        slot = find_earliest_slot(merged, window_start, window_end, duration)
        if slot is not None:
            start_str = minutes_to_time(slot)
            end_str = minutes_to_time(slot + duration)
            return f'Here is the proposed time: {day}, {start_str} - {end_str}'
    
    return None


def parse_duration(text):
    # Look for duration patterns
    m = re.search(r'(\d+)\s*-?\s*minute', text.lower())
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*-?\s*hour', text.lower())
    if m:
        return int(m.group(1)) * 60
    m = re.search(r'half\s*-?\s*hour', text.lower())
    if m:
        return 30
    m = re.search(r'1-hour', text.lower())
    if m:
        return 60
    # Check for "30 minutes" or "30-minute"
    m = re.search(r'(\d+)\s*min', text.lower())
    if m:
        return int(m.group(1))
    return None


def time_to_minutes(time_str):
    time_str = time_str.strip()
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time(minutes):
    h = minutes // 60
    m = minutes % 60
    return f'{h:02d}:{m:02d}'


def format_time_str(t):
    """Ensure HH:MM format"""
    parts = t.split(':')
    h = int(parts[0])
    m = int(parts[1])
    return f'{h:02d}:{m:02d}'


def parse_time_window(text):
    m = re.search(r'between\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', text)
    if m:
        return time_to_minutes(m.group(1)), time_to_minutes(m.group(2))
    m = re.search(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', text)
    if m:
        return time_to_minutes(m.group(1)), time_to_minutes(m.group(2))
    return 9 * 60, 17 * 60


def parse_days(text):
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    # Look for "on Monday, Tuesday, or Wednesday" or "on Monday" patterns
    # First try explicit day listing
    m = re.search(r'on\s+((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:\s*,\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))*(?:\s*,?\s*(?:and|or)\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))?)', text)
    if m:
        day_text = m.group(1)
        found = re.findall(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', day_text)
        if found:
            # Preserve order
            return list(dict.fromkeys(found))
    
    # Try "Monday, Tuesday or Wednesday" pattern without "on"
    m = re.search(r'((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:\s*,\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))*(?:\s*,?\s*(?:and|or)\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))?)', text)
    if m:
        day_text = m.group(1)
        found = re.findall(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', day_text)
        if found and len(found) > 1:
            return list(dict.fromkeys(found))
    
    # Single day mention
    for day in day_names:
        if day in text:
            return [day]
    
    return ['Monday']


def parse_busy_times(text, days):
    """Parse busy times for each participant, organized by day."""
    busy_times = {}
    
    # Find participant names and their busy times
    # Pattern: "Name: busy TIME-TIME, TIME-TIME" or "Name busy: TIME-TIME"
    # Also handle multi-day: "Name busy: Monday: times; Tuesday: times"
    
    # First, try to find all participant busy time declarations
    # Pattern variations:
    # 1. "Name: busy HH:MM-HH:MM, HH:MM-HH:MM"
    # 2. "Name busy: HH:MM-HH:MM, HH:MM-HH:MM"  
    # 3. "Name: free all day"
    # 4. "Name busy: Monday: times; Tuesday: times"
    # 5. "Name's busy times: Monday times, Tuesday times"
    
    sentences = re.split(r'(?<=[.])\s+', text)
    
    # Try multi-day busy pattern first
    # "Name busy: Monday: 9:00-9:30, 10:00-10:30; Tuesday: 9:00-9:30"
    multi_day_pattern = re.finditer(
        r"(\w+?)(?:'s)?\s+busy(?:\s+times)?[:]\s*((?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[\s:]+[\d:,\s\-]+[;.]?\s*)+)",
        text
    )
    
    found_multi = set()
    for m in multi_day_pattern:
        name = m.group(1)
        schedule_text = m.group(2)
        
        # Check if this actually contains day names in the busy spec
        day_sections = re.finditer(
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[:\s]+([\d:,\s\-]+?)(?=(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|$|[;])',
            schedule_text
        )
        
        person_busy = {}
        has_days = False
        for ds in day_sections:
            has_days = True
            day = ds.group(1)
            times_text = ds.group(2)
            intervals = parse_time_intervals(times_text)
            if day not in person_busy:
                person_busy[day] = []
            person_busy[day].extend(intervals)
        
        if has_days:
            found_multi.add(name)
            busy_times[name] = person_busy
    
    # Also try pattern: "Name busy: Day: times; Day: times" with semicolons
    multi_day_pattern2 = re.finditer(
        r"(\w+)\s+busy:\s*((?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?::\s*|\s+)[\d:,\s\-]+(?:;\s*)?)+)",
        text
    )
    for m in multi_day_pattern2:
        name = m.group(1)
        if name in found_multi:
            continue
        schedule_text = m.group(2)
        day_sections = re.finditer(
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[:\s]+([\d:,\s\-]+?)(?=(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|$|[;])',
            schedule_text
        )
        person_busy = {}
        has_days = False
        for ds in day_sections:
            has_days = True
            day = ds.group(1)
            times_text = ds.group(2)
            intervals = parse_time_intervals(times_text)
            if day not in person_busy:
                person_busy[day] = []
            person_busy[day].extend(intervals)
        if has_days:
            found_multi.add(name)
            busy_times[name] = person_busy

    # Now handle single-day busy patterns
    # "Name: busy HH:MM-HH:MM, HH:MM-HH:MM"
    # "Name busy: HH:MM-HH:MM, HH:MM-HH:MM"
    # "Name: free all day"
    
    # Various patterns for single-day busy times
    patterns = [
        r"(\w+):\s*busy\s+([\d:,\s\-]+?)(?=[.;]|$|\s+\w+[\s:]+(?:busy|free))",
        r"(\w+)\s+busy:\s+([\d:,\s\-]+?)(?=[.;]|$|\s+\w+[\s:]+(?:busy|free))",
        r"(\w+):\s*busy\s+([\d:,\s\-]+)",
        r"(\w+)\s+busy:\s+([\d:,\s\-]+)",
    ]
    
    # More targeted approach: split text by participant declarations
    # Find patterns like "Name: busy ..." or "Name busy: ..."
    single_busy = re.finditer(
        r'(\w+)(?:\s*:\s*busy\s+|\s+busy:\s+)([\d:,\s\-]+?)(?=\.\s+\w+|$|\.\s*$|;\s*\w+|\s+\w+\s*:\s*(?:busy|free)|\s+\w+\s+busy:)',
        text
    )
    
    for m in single_busy:
        name = m.group(1)
        if name in found_multi or name.lower() in ['not', 'is', 'are', 'the', 'and', 'or', 'on', 'for', 'all', 'between']:
            continue
        times_text = m.group(2).strip().rstrip('.')
        intervals = parse_time_intervals(times_text)
        if intervals and name not in busy_times:
            person_busy = {}
            for day in days:
                person_busy[day] = list(intervals)
            busy_times[name] = person_busy
    
    # Handle "free all day"
    free_pattern = re.finditer(r'(\w+):\s*free\s+all\s+day', text)
    for m in free_pattern:
        name = m.group(1)
        if name not in busy_times:
            busy_times[name] = {day: [] for day in days}
    
    # Handle "with Name busy at TIME-TIME" pattern
    with_busy = re.finditer(
        r'with\s+(\w+)\s+busy\s+(?:at\s+)?([\d:,\s\-]+?)(?:\s+and\s+(\w+)\s+busy\s+(?:at\s+)?([\d:,\s\-]+))?',
        text
    )
    for m in with_busy:
        name1 = m.group(1)
        times1 = m.group(2).strip().rstrip('.')
        if name1 not in busy_times:
            intervals = parse_time_intervals(times1)
            if intervals:
                busy_times[name1] = {day: list(intervals) for day in days}
        if m.group(3):
            name2 = m.group(3)
            times2 = m.group(4).strip().rstrip('.')
            if name2 not in busy_times:
                intervals = parse_time_intervals(times2)
                if intervals:
                    busy_times[name2] = {day: list(intervals) for day in days}
    
    # Handle "Participants busy times:" pattern
    participants_pattern = re.search(
        r'(?:Participants?\s+)?busy\s+times?:\s*(.*)',
        text, re.DOTALL
    )
    if participants_pattern and not busy_times:
        remainder = participants_pattern.group(1)
        person_matches = re.finditer(
            r'(\w+):\s*([\d:,\s\-]+?)(?=;\s*\w+:|$)',
            remainder
        )
        for pm in person_matches:
            name = pm.group(1)
            if name not in busy_times and name not in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                times_text = pm.group(2).strip().rstrip('.')
                intervals = parse_time_intervals(times_text)
                if intervals:
                    busy_times[name] = {day: list(intervals) for day in days}
    
    # Another attempt for the semicolon-separated pattern within "Participants busy times:"
    part_busy_pattern = re.search(r'(?:Participants?\s+)?busy\s+times:\s*((?:\w+:\s*[\d:,\s\-]+;\s*)*\w+:\s*[\d:,\s\-]+)', text)
    if part_busy_pattern:
        remainder = part_busy_pattern.group(1)
        entries = re.split(r';\s*', remainder)
        for entry in entries:
            em = re.match(r'(\w+):\s*(.*)', entry.strip())
            if em:
                name = em.group(1)
                if name in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                    continue
                times_text = em.group(2).strip().rstrip('.')
                if 'free' in times_text.lower():
                    if name not in busy_times:
                        busy_times[name] = {day: [] for day in days}
                else:
                    intervals = parse_time_intervals(times_text)
                    if intervals and name not in busy_times:
                        busy_times[name] = {day: list(intervals) for day in days}
    
    # Handle: "Name busy: Day TIME-TIME, TIME-TIME" (single line with day prefix for single day)
    single_day_busy = re.finditer(
        r'(\w+)\s+busy:\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+([\d:,\s\-]+?)(?=[.;]|$)',
        text
    )
    for m in single_day_busy:
        name = m.group(1)
        day = m.group(2)
        if name not in found_multi and name not in busy_times:
            times_text = m.group(3).strip()
            intervals = parse_time_intervals(times_text)
            if intervals:
                busy_times[name] = {day: intervals}

    return busy_times


def parse_time_intervals(times_text):
    """Parse time intervals from text like '9:00-10:00, 11:30-12:00'"""
    intervals = []
    matches = re.finditer(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', times_text)
    for m in matches:
        start = time_to_minutes(m.group(1))
        end = time_to_minutes(m.group(2))
        intervals.append((start, end))
    return intervals


def parse_preferences(text):
    """Parse day and time preferences."""
    day_prefs = {}  # person -> list of avoided days
    time_constraints = {}  # person -> list of (type, minutes)
    
    # "Name prefers not Day"
    pref_pattern = re.finditer(r'(\w+)\s+prefers\s+not\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text)
    for m in pref_pattern:
        name = m.group(1)
        day = m.group(2)
        if name not in day_prefs:
            day_prefs[name] = []
        day_prefs[name].append(day)
    
    # "Name cannot meet on Day"
    cannot_day = re.finditer(r'(\w+)\s+cannot\s+meet\s+on\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text)
    for m in cannot_day:
        name = m.group(1)
        day = m.group(2)
        if name not in day_prefs:
            day_prefs[name] = []
        day_prefs[name].append(day)
    
    # "Name doesn't want to meet after HH:MM"
    after_pattern = re.finditer(r"(\w+)\s+doesn'?t\s+want\s+to\s+meet\s+after\s+(\d{1,2}:\d{2})", text)
    for m in after_pattern:
        name = m.group(1)
        t = time_to_minutes(m.group(2))
        if name not in time_constraints:
            time_constraints[name] = []
        time_constraints[name].append(('not_after', t))
    
    # "Name cannot meet before HH:MM"
    before_pattern = re.finditer(r'(\w+)\s+cannot\s+meet\s+before\s+(\d{1,2}:\d{2})', text)
    for m in before_pattern:
        name = m.group(1)
        t = time_to_minutes(m.group(2))
        if name not in time_constraints:
            time_constraints[name] = []
        time_constraints[name].append(('not_before', t))
    
    # "Name doesn't want Tuesday" - day preference
    doesnt_want_day = re.finditer(r"(\w+)\s+doesn'?t\s+want\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", text)
    for m in doesnt_want_day:
        name = m.group(1)
        day = m.group(2)
        if name not in day_prefs:
            day_prefs[name] = []
        day_prefs[name].append(day)
    
    return day_prefs, time_constraints


def merge_intervals(intervals):
    """Merge overlapping intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def find_earliest_slot(busy_intervals, window_start, window_end, duration):
    """Find earliest free slot of given duration within window."""
    merged = merge_intervals(busy_intervals)
    
    current = window_start
    for busy_start, busy_end in merged:
        if current + duration <= busy_start:
            return current
        if busy_end > current:
            current = busy_end
    
    if current + duration <= window_end:
        return current
    
    return None
