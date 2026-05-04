"""Auto-generated code-distilled implementation for propose_meeting_time_2."""

import re
from datetime import datetime, timedelta

def propose_meeting_time_2(text):
    # Parse duration
    duration_minutes = None
    if '1-hour' in text or '1 hour' in text or 'one hour' in text:
        duration_minutes = 60
    elif '30-minute' in text or '30 minute' in text or 'half an hour' in text or 'half hour' in text:
        duration_minutes = 30
    elif '2-hour' in text or '2 hour' in text:
        duration_minutes = 120
    
    if duration_minutes is None:
        # Try to find duration pattern
        m = re.search(r'(\d+)-minute', text)
        if m:
            duration_minutes = int(m.group(1))
        else:
            m = re.search(r'(\d+)\s*minute', text)
            if m:
                duration_minutes = int(m.group(1))
            else:
                duration_minutes = 30  # default
    
    # Parse available days
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    available_days = []
    # Check for "on Monday, Tuesday or Wednesday" or "on Monday"
    day_pattern = re.search(r'on\s+((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:\s*,\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))*(?:\s+(?:or|and)\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))?)', text)
    if day_pattern:
        day_str = day_pattern.group(1)
        for d in days_order:
            if d in day_str:
                available_days.append(d)
    
    if not available_days:
        # Look for day mentions in context
        for d in days_order:
            if d in text:
                available_days.append(d)
    
    if not available_days:
        available_days = ['Monday']
    
    # Remove duplicates while preserving order
    seen = set()
    unique_days = []
    for d in available_days:
        if d not in seen:
            seen.add(d)
            unique_days.append(d)
    available_days = unique_days
    
    # Parse time window
    window_match = re.search(r'between\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', text)
    if window_match:
        window_start = _parse_time(window_match.group(1))
        window_end = _parse_time(window_match.group(2))
    else:
        # Check for time window like "9:00-17:00"
        window_match2 = re.search(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s*(?:work\s*hours|hours)', text)
        if window_match2:
            window_start = _parse_time(window_match2.group(1))
            window_end = _parse_time(window_match2.group(2))
        else:
            window_start = _parse_time('9:00')
            window_end = _parse_time('17:00')
    
    # Parse "cannot meet on" constraints
    cannot_meet = {}
    cannot_patterns = re.finditer(r'(\w+)\s+cannot\s+meet\s+on\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text)
    for m in cannot_patterns:
        name = m.group(1)
        day = m.group(2)
        if name not in cannot_meet:
            cannot_meet[name] = set()
        cannot_meet[name].add(day)
    
    # Parse busy times per person per day
    # We need to handle multiple formats
    all_busy = {}  # day -> list of (start, end) tuples
    
    for day in available_days:
        all_busy[day] = []
    
    # Strategy: extract all busy time intervals and associate them with days and people
    # This is complex due to varied formats
    
    # First, let's try to parse structured busy times
    # Format variations:
    # "Margaret busy: Monday 10:00-10:30, 11:30-12:30; Tuesday 11:00-11:30"
    # "Kyle busy: 9:30-10:00, 12:30-13:00" (single day context)
    # "Danielle: free all day"
    # "Angela: 9:00-10:00, 10:30-11:30"
    # "Jacqueline (busy: 9:00-9:30, 10:30-11:30, ...)"
    
    _parse_busy_times(text, available_days, all_busy, cannot_meet)
    
    # Now find the earliest available slot
    duration = timedelta(minutes=duration_minutes)
    
    for day in available_days:
        busy_intervals = sorted(all_busy[day], key=lambda x: x[0])
        # Merge overlapping intervals
        merged = _merge_intervals(busy_intervals)
        
        # Find free slots
        slot_start = window_start
        for busy_start, busy_end in merged:
            if slot_start + duration <= busy_start:
                # Found a free slot
                return f'Here is the proposed time: {day}, {_format_time(slot_start)} - {_format_time(slot_start + duration)}'
            if busy_end > slot_start:
                slot_start = busy_end
        
        # Check after last busy period
        if slot_start + duration <= window_end:
            return f'Here is the proposed time: {day}, {_format_time(slot_start)} - {_format_time(slot_start + duration)}'
    
    return None


def _parse_time(t_str):
    parts = t_str.strip().split(':')
    return timedelta(hours=int(parts[0]), minutes=int(parts[1]))


def _format_time(td):
    total_minutes = int(td.total_seconds()) // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f'{hours}:{minutes:02d}'


def _merge_intervals(intervals):
    if not intervals:
        return []
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _parse_busy_times(text, available_days, all_busy, cannot_meet):
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Handle "cannot meet" constraints - block entire day
    for name, blocked_days in cannot_meet.items():
        for day in blocked_days:
            if day in all_busy:
                all_busy[day].append((_parse_time('0:00'), _parse_time('23:59')))
    
    # Time range pattern
    time_range_pat = r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})'
    
    # Check if this is a multi-day format (days appear in busy specs)
    has_multi_day = False
    for day in days_order:
        # Check if day appears in busy time context (not just in "on Monday" part)
        if text.count(day) > 1 or re.search(r'(?:busy|:)\s*' + day, text):
            has_multi_day = True
            break
    
    # Also check format like "Monday 10:00-10:30" in busy sections
    if re.search(r'(?:busy:\s*)(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}:\d{2}', text):
        has_multi_day = True
    
    if has_multi_day and len(available_days) > 1:
        # Multi-day format: parse per-person sections with day labels
        # Find person sections
        # Pattern: "PersonName busy: Day times; Day times" or "PersonName: Day times"
        person_sections = re.split(r'(?<=[.;])\s*(?=[A-Z][a-z]+\s+(?:busy|free|:))', text)
        
        # Alternative: find all person busy declarations
        # "Margaret busy: Monday 10:00-10:30, ..."
        person_pattern = re.finditer(
            r'(\b[A-Z][a-z]+)\s+(?:busy:\s*|:\s*busy\s+)(.*?)(?=\.\s*[A-Z]|\.\s*$|$)',
            text, re.DOTALL
        )
        
        # Let me try a different approach: split by person name followed by busy/free
        # First extract the scheduling part after the initial description
        segments = re.split(r'\.\s+', text)
        
        for segment in segments:
            _parse_segment_multiday(segment, available_days, all_busy)
    else:
        # Single day or simple format
        if len(available_days) == 1:
            default_day = available_days[0]
        else:
            default_day = available_days[0]
        
        _parse_segment_singleday(text, default_day, all_busy, available_days)


def _parse_segment_multiday(segment, available_days, all_busy):
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    time_range_pat = r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})'
    
    # Find person busy declarations with day labels
    # e.g., "Margaret busy: Monday 10:00-10:30, 11:30-12:30; Tuesday 11:00-11:30"
    # Split by person
    person_parts = re.finditer(
        r'([A-Z][a-z]+)\s+busy:\s*(.*?)(?=(?:[A-Z][a-z]+\s+(?:busy|free|cannot))|$)',
        segment, re.DOTALL
    )
    
    for pp in person_parts:
        busy_text = pp.group(2)
        current_day = None
        
        # Split by semicolons for different days
        day_sections = re.split(r';\s*', busy_text)
        for ds in day_sections:
            # Check if a day is mentioned
            for d in days_order:
                if d in ds:
                    current_day = d
                    break
            
            if current_day and current_day in all_busy:
                ranges = re.findall(time_range_pat, ds)
                for start_s, end_s in ranges:
                    all_busy[current_day].append((_parse_time(start_s), _parse_time(end_s)))


def _parse_segment_singleday(text, default_day, all_busy, available_days):
    time_range_pat = r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})'
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # For multi-day in single-day parser (like example 1 with Margaret/Tyler)
    # Check if the text has day names associated with busy times
    has_day_labels_in_busy = False
    for d in days_order:
        if re.search(d + r'\s+\d{1,2}:\d{2}', text):
            has_day_labels_in_busy = True
            break
    
    if has_day_labels_in_busy:
        # Parse with day context
        # Find person sections
        # Split text by person identifiers
        # Pattern: "Name busy:" or "Name:" followed by schedule
        parts = re.split(r'(?:^|[.;])\s*', text)
        
        # Better approach: find all person+busy sections
        # "Margaret busy: Monday 10:00-10:30, 11:30-12:30, 13:30-14:00, 14:30-17:00; Tuesday ..."
        person_matches = list(re.finditer(
            r'([A-Z][a-z]+)\s+(?:busy:\s*|busy\s+)((?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+[\d:,\s–-]+[;.]?\s*)+)',
            text, re.DOTALL
        ))
        
        if not person_matches:
            # Try alternative pattern
            person_matches = list(re.finditer(
                r'([A-Z][a-z]+)\s+busy:\s*(.*?)(?=\s*[A-Z][a-z]+\s+(?:busy|free|cannot)|$)',
                text, re.DOTALL
            ))
        
        for pm in person_matches:
            busy_text = pm.group(2)
            current_day = None
            
            # Process tokens
            day_sections = re.split(r';\s*', busy_text)
            for ds in day_sections:
                for d in days_order:
                    if d in ds:
                        current_day = d
                        break
                
                if current_day and current_day in all_busy:
                    ranges = re.findall(time_range_pat, ds)
                    for start_s, end_s in ranges:
                        all_busy[current_day].append((_parse_time(start_s), _parse_time(end_s)))
        
        # Handle "cannot meet" already handled above
        # Check for "cannot meet on Day" in text
        cannot_patterns = re.finditer(r'(\w+)\s+cannot\s+meet\s+on\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text)
        for m in cannot_patterns:
            day = m.group(2)
            if day in all_busy:
                all_busy[day].append((_parse_time('0:00'), _parse_time('23:59')))
        
        return
    
    # Single day format - all times belong to default_day (or the mentioned day)
    # But we may have multiple days mentioned in context
    # Determine the actual day for busy times
    
    # Find all time ranges in the text, but skip the window specification
    # First remove the window part
    cleaned = re.sub(r'between\s+\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}', '', text)
    cleaned = re.sub(r'\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}\s*(?:work\s*hours|hours)', '', cleaned)
    
    # Determine which day busy times apply to
    # Check for day mentions
    active_day = default_day
    for d in days_order:
        if d in text:
            active_day = d
            break
    
    # Handle person-by-person parsing
    # Try to find person sections
    # Various formats:
    # "Name busy: times" or "Name: busy times" or "Name: times" or "Name (busy: times)"
    
    # First try parenthetical format: "Name (busy: ...)"
    paren_matches = re.finditer(r'([A-Z][a-z]+)\s*\(busy:\s*(.*?)\)', text)
    found_paren = False
    for pm in paren_matches:
        found_paren = True
        busy_text = pm.group(2)
        if 'free' not in busy_text.lower():
            ranges = re.findall(time_range_pat, busy_text)
            for start_s, end_s in ranges:
                if active_day in all_busy:
                    all_busy[active_day].append((_parse_time(start_s), _parse_time(end_s)))
    
    if found_paren:
        # Also check for non-parenthetical entries
        # Like "Billy (free)" - no busy times
        # Check if there are also non-paren busy declarations
        remaining = re.sub(r'[A-Z][a-z]+\s*\(busy:.*?\)', '', text)
        remaining = re.sub(r'[A-Z][a-z]+\s*\(free\)', '', remaining)
        # Parse any remaining busy times from the remaining text
        _parse_remaining_busy(remaining, active_day, all_busy, time_range_pat, days_order)
        return
    
    # Try "Name busy: times" or "Name: busy times" format
    # Split by person declarations
    # Pattern: "Name busy:" or "Name:" 
    person_sections = re.finditer(
        r'([A-Z][a-z]+)(?:\s+busy)?:\s*(.*?)(?=(?:\.\s+)?[A-Z][a-z]+(?:\s+busy)?:|$)',
        text, re.DOTALL
    )
    
    found_sections = False
    for ps in person_sections:
        name = ps.group(1)
        busy_text = ps.group(2).strip()
        found_sections = True
        
        # Skip if "free all day" or similar
        if 'free' in busy_text.lower() and ('all day' in busy_text.lower() or busy_text.lower().startswith('free')):
            continue
        
        # Check for "busy" keyword followed by times
        busy_part = busy_text
        busy_match = re.match(r'busy\s+(.*)', busy_text, re.DOTALL)
        if busy_match:
            busy_part = busy_match.group(1)
        
        ranges = re.findall(time_range_pat, busy_part)
        for start_s, end_s in ranges:
            if active_day in all_busy:
                all_busy[active_day].append((_parse_time(start_s), _parse_time(end_s)))
    
    if found_sections:
        return
    
    # Fallback: just find all time ranges in the text (excluding window)
    _parse_remaining_busy(cleaned, active_day, all_busy, time_range_pat, days_order)


def _parse_remaining_busy(text, active_day, all_busy, time_range_pat, days_order):
    # Look for busy time ranges, possibly with day context
    # Check for day labels
    current_day = active_day
    
    # Find all time ranges with possible day context
    # Tokenize by finding days and time ranges
    tokens = []
    pos = 0
    pattern = re.compile(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|(\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2})')
    for m in pattern.finditer(text):
        if m.group(1):
            current_day = m.group(1)
        elif m.group(2):
            tr = re.match(time_range_pat, m.group(2))
            if tr and current_day in all_busy:
                all_busy[current_day].append((_parse_time(tr.group(1)), _parse_time(tr.group(2))))
    
    # Also parse from structured sections with names
    # "Amber: 10:00-10:30, ..."
    sections = re.finditer(r'([A-Z][a-z]+):\s*([\d:,\s–-]+?)(?=;|[A-Z][a-z]+:|$)', text)
    for s in sections:
        busy_text = s.group(2)
        ranges = re.findall(time_range_pat, busy_text)
        for start_s, end_s in ranges:
            if active_day in all_busy:
                all_busy[active_day].append((_parse_time(start_s), _parse_time(end_s)))
