"""Auto-generated workflow-distilled implementation for calendar_scheduling.

Tools from benchmarks/natural_plan/learned_class3_v3/20260428.234714.calendar_scheduling__ptool_inducer/learned_ptools.py are inlined below.
"""

"""Induced ptools for calendar_scheduling."""

from secretagent.core import implement_via


@implement_via('simulate')
def propose_meeting_time(focus: str) -> str:
    """
    Reasons about potential meeting times by analyzing participant calendars and the required duration.
    The function should extract the day of the week and specific time window from the agent's focus.
    The response should be a structured string in the format: "Here is the proposed time: [Day], [Start Time] - [End Time]".
    The agent should pay attention to ensuring the proposed time does not conflict with any known busy periods
    and that the end time is exactly the duration after the start time.
    Returns:
        str: A formatted string proposing a specific time slot.
        Example: "Here is the proposed time: Monday, 13:30 - 14:00"
    """


@implement_via('simulate')
def propose_meeting_time_2(focus: str) -> str:
    """
    Proposes a specific meeting time slot based on participant availability and meeting duration.

    This function analyzes the current context to identify available time slots where all
    participants are free for the requested meeting duration. It considers:
    - Each participant's calendar busy times
    - The required meeting duration
    - Working hours and timezone considerations
    - Previously attempted time slots to avoid repetition

    The response should be structured as: 'Here is the proposed time: [Day], [Start Time] - [End Time]'
    where times are in 24-hour format (HH:MM) and day is a weekday name.

    Pay attention to:
    - Ensuring the proposed time doesn't conflict with any participant's busy times
    - Using the next available slot if multiple options exist
    - Formatting the output exactly as specified
    - Considering timezone differences if participants are in different timezones

    Returns:
        str: A formatted string proposing a specific meeting time
        Example: 'Here is the proposed time: Monday, 14:30 - 15:30'
    """




import re
from datetime import datetime, timedelta

def calendar_scheduling(prompt):
    # Parse the problem from the prompt
    # Extract the actual task (last TASK in the prompt)
    tasks = prompt.split('TASK:')
    if len(tasks) < 2:
        return None
    
    # The last TASK is the one we need to solve
    task_text = tasks[-1]
    
    # Extract duration
    duration_minutes = None
    if 'half an hour' in task_text or '30 minutes' in task_text or '30-minute' in task_text:
        duration_minutes = 30
    elif 'one hour' in task_text or '60 minutes' in task_text or '1 hour' in task_text:
        duration_minutes = 60
    elif 'one and a half hour' in task_text or '90 minutes' in task_text:
        duration_minutes = 90
    elif 'two hour' in task_text or '120 minutes' in task_text:
        duration_minutes = 120
    
    if duration_minutes is None:
        # Try to find duration pattern
        dur_match = re.search(r'for (\d+) minutes', task_text)
        if dur_match:
            duration_minutes = int(dur_match.group(1))
        else:
            return None
    
    # Extract work hours
    work_match = re.search(r'work hours of (\d+:\d+) to (\d+:\d+)', task_text)
    if work_match:
        work_start = work_match.group(1)
        work_end = work_match.group(2)
    else:
        work_start = '9:00'
        work_end = '17:00'
    
    def time_to_min(t):
        parts = t.strip().split(':')
        return int(parts[0]) * 60 + int(parts[1])
    
    def min_to_time(m):
        h = m // 60
        mi = m % 60
        return f"{h}:{mi:02d}"
    
    ws = time_to_min(work_start)
    we = time_to_min(work_end)
    
    # Extract days
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Find which days are allowed
    day_match = re.search(r'on (?:either )?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:(?:,\s*| or )(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))*', task_text.split('\n')[0] if '\n' in task_text else task_text[:500])
    
    allowed_days = []
    # More robust: search in the first sentence/paragraph
    first_part = task_text.split('\n')[0] if '\n' in task_text else task_text[:500]
    for day in days_order:
        if day in first_part:
            allowed_days.append(day)
    
    if not allowed_days:
        # Try broader search
        for day in days_order:
            if day in task_text[:500]:
                allowed_days.append(day)
    
    if not allowed_days:
        return None
    
    # Sort days by their natural order
    allowed_days = sorted(set(allowed_days), key=lambda d: days_order.index(d))
    
    # Extract participant names
    name_match = re.search(r'schedule a meeting for (.+?) for (?:half an hour|one hour|one and a half|two hour|\d+ minute)', task_text)
    if not name_match:
        return None
    
    names_str = name_match.group(1)
    # Parse names: "A, B, C and D" or "A and B"
    names_str = names_str.replace(' and ', ', ')
    participants = [n.strip() for n in names_str.split(',') if n.strip()]
    
    # Parse busy times for each participant on each day
    # Build a dict: {(person, day): [(start_min, end_min), ...]}
    busy = {}
    
    for p in participants:
        for day in allowed_days:
            busy[(p, day)] = []
    
    # Parse schedule info
    # Various patterns:
    # "X has blocked their calendar on Monday during 9:00 to 10:00, 11:00 to 12:00"
    # "X has meetings on Monday during 9:00 to 10:00"
    # "X is free the entire day" / "X has no meetings the whole week"
    # "X has no meetings on Monday"
    # "X is busy on Monday from 9:00 to 10:00"
    
    schedule_section = task_text
    
    # Find all time blocks for each person
    # Split by person mentions
    lines = schedule_section.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Find which participant this line is about
        person = None
        for p in participants:
            if line.startswith(p) or line.startswith(p.lower()):
                person = p
                break
        
        if person is None:
            continue
        
        # Check for "free" or "no meetings"
        if 'free the entire day' in line.lower() or 'no meetings the whole week' in line.lower() or 'has no meetings' in line.lower() or 'is free' in line.lower():
            # Check if specific day mentioned
            for day in allowed_days:
                if day in line:
                    busy[(person, day)] = []
            if 'whole week' in line.lower() or 'entire week' in line.lower():
                for day in allowed_days:
                    busy[(person, day)] = []
            continue
        
        # Find day mentions and time ranges in this line
        # Pattern: "on Monday during 9:00 to 10:00, 11:00 to 12:00"
        # Could also span multiple days in one line
        
        for day in allowed_days:
            if day in line:
                # Find all time ranges after this day mention
                # Get the portion of line related to this day
                day_idx = line.index(day)
                # Find next day mention or end of line
                next_day_idx = len(line)
                for other_day in allowed_days:
                    if other_day != day and other_day in line[day_idx + len(day):]:
                        idx = line.index(other_day, day_idx + len(day))
                        if idx < next_day_idx:
                            next_day_idx = idx
                
                segment = line[day_idx:next_day_idx]
                
                # Find all time ranges: HH:MM to HH:MM
                time_ranges = re.findall(r'(\d{1,2}:\d{2})\s*to\s*(\d{1,2}:\d{2})', segment)
                for start_t, end_t in time_ranges:
                    s = time_to_min(start_t)
                    e = time_to_min(end_t)
                    busy[(person, day)].append((s, e))
    
    # Also handle multi-day lines like "X has blocked their calendar on Monday during ... and on Tuesday during ..."
    # The above loop should handle it since we search for each day in the line
    
    # Check for preferences
    preference = None
    pref_match_early = re.search(r'[Pp]refer.*(?:earlier|morning|early)', task_text)
    pref_match_late = re.search(r'[Pp]refer.*(?:later|afternoon|late|evening)', task_text)
    if pref_match_early:
        preference = 'early'
    elif pref_match_late:
        preference = 'late'
    
    # Now find the earliest (or latest if preferred) available slot
    for day in allowed_days:
        # Collect all busy intervals for this day
        all_busy = []
        for p in participants:
            all_busy.extend(busy.get((p, day), []))
        
        # Sort and merge busy intervals
        all_busy.sort()
        merged = []
        for s, e in all_busy:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        
        # Find free slots
        candidates = []
        current = ws
        for s, e in merged:
            if s > current:
                # Free from current to s
                if s - current >= duration_minutes:
                    candidates.append(current)
            current = max(current, e)
        # Check after last busy block
        if we - current >= duration_minutes:
            candidates.append(current)
        
        if candidates:
            if preference == 'late':
                # Find the latest possible start
                # Go through free slots and find latest start
                best = None
                current = ws
                for s, e in merged:
                    if s > current and s - current >= duration_minutes:
                        # Latest start in this gap
                        latest_start = s - duration_minutes
                        best = latest_start
                    current = max(current, e)
                if we - current >= duration_minutes:
                    best = we - duration_minutes
                
                if best is not None:
                    start = best
                    end = start + duration_minutes
                    return f"Here is the proposed time: {day}, {min_to_time(start)} - {min_to_time(end)} "
            else:
                # Earliest
                start = candidates[0]
                end = start + duration_minutes
                return f"Here is the proposed time: {day}, {min_to_time(start)} - {min_to_time(end)} "
    
    # If pure Python approach failed, fall back to LLM tools
    try:
        # Build a detailed description for the tool
        result1 = propose_meeting_time(task_text.strip()[:500])
        result2 = propose_meeting_time_2(task_text.strip()[:800])
        
        # Try to validate results
        for result in [result1, result2]:
            if result and 'Here is the proposed time:' in result:
                # Ensure trailing space
                result = result.strip() + ' '
                return result
    except Exception:
        pass
    
    return None
