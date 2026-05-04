"""Auto-generated code-distilled implementation for calendar_scheduling."""

import re
from datetime import datetime, timedelta


def calendar_scheduling(prompt: str) -> str:
    if not prompt or not isinstance(prompt, str):
        return None
    
    try:
        # Extract the TASK section (the last TASK in the prompt, which is the actual task)
        # The prompt contains example tasks and then the actual task
        tasks = prompt.split("TASK:")
        if len(tasks) < 2:
            return None
        
        # The last TASK block is the one we need to solve
        actual_task = tasks[-1]
        
        # Extract participants
        participants_match = re.search(r'You need to schedule a meeting for (.*?) for (half an hour|one hour|one and a half hours|two hours)', actual_task)
        if not participants_match:
            return None
        
        participants_str = participants_match.group(1)
        duration_str = participants_match.group(2)
        
        # Parse participants
        # Handle "A, B and C" or "A and B" formats
        participants_str = participants_str.replace(' and ', ', ')
        participants = [p.strip() for p in participants_str.split(',') if p.strip()]
        
        # Parse duration in minutes
        duration_map = {
            'half an hour': 30,
            'one hour': 60,
            'one and a half hours': 90,
            'two hours': 120,
        }
        duration = duration_map.get(duration_str, 30)
        
        # Extract work hours
        work_hours_match = re.search(r'work hours of (\d{1,2}:\d{2}) to (\d{1,2}:\d{2})', actual_task)
        if work_hours_match:
            work_start = parse_time(work_hours_match.group(1))
            work_end = parse_time(work_hours_match.group(2))
        else:
            work_start = parse_time("9:00")
            work_end = parse_time("17:00")
        
        # Extract available days
        days_match = re.search(r'on (?:either )?(Monday(?:,\s*Tuesday)?(?:,\s*Wednesday)?(?:,\s*Thursday)?(?:,\s*Friday)?(?:\s*or\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday))?|Monday|Tuesday|Wednesday|Thursday|Friday)', actual_task)
        available_days = []
        if days_match:
            days_text = days_match.group(0)
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                if day in days_text:
                    available_days.append(day)
        
        if not available_days:
            available_days = ['Monday']
        
        # Extract schedules for each participant
        schedules = {}
        for participant in participants:
            schedules[participant] = {}
            for day in available_days:
                schedules[participant][day] = []
        
        # Parse the existing schedules section
        schedule_section = actual_task
        
        # Find each participant's schedule
        for participant in participants:
            # Look for patterns like "Name has..." or "Name's schedule"
            # Pattern: "Name: busy from X to Y, ..." or various formats
            
            # Try to find busy times for each day
            for day in available_days:
                busy_times = extract_busy_times(schedule_section, participant, day, available_days)
                schedules[participant][day] = busy_times
        
        # Extract preferences
        preferences = extract_preferences(actual_task, participants)
        
        # Find the earliest available slot
        result = find_meeting_slot(participants, schedules, available_days, work_start, work_end, duration, preferences)
        
        if result is None:
            return None
        
        best_day, best_start, best_end = result
        
        start_str = format_time(best_start)
        end_str = format_time(best_end)
        
        # Build detailed response
        response_parts = []
        
        # Add analysis
        response_parts.append(f"Based on the analysis of all participants' schedules, ")
        response_parts.append(f"I need to find a {duration}-minute time slot that works for everyone.\n\n")
        
        # Add schedule summary
        response_parts.append("Analyzing busy periods:\n")
        for participant in participants:
            day_schedules = schedules[participant].get(best_day, [])
            if day_schedules:
                busy_strs = [f"{format_time(s)}-{format_time(e)}" for s, e in day_schedules]
                response_parts.append(f"- {participant}: Busy {', '.join(busy_strs)}\n")
            else:
                response_parts.append(f"- {participant}: Free all day\n")
        
        response_parts.append(f"\nHere is the proposed time: {best_day}, {start_str} - {end_str}\n\n")
        response_parts.append(f"This time slot works because:\n")
        
        for participant in participants:
            day_schedules = schedules[participant].get(best_day, [])
            if day_schedules:
                busy_strs = [f"{format_time(s)}-{format_time(e)}" for s, e in day_schedules]
                response_parts.append(f"- {participant}: Free during {start_str}-{end_str} (busy periods: {', '.join(busy_strs)})\n")
            else:
                response_parts.append(f"- {participant}: Free all day (no conflicts)\n")
        
        dur_str = f"{duration}-minute" if duration != 60 else "1-hour"
        response_parts.append(f"- The {dur_str} duration fits within the {format_time(work_start)}-{format_time(work_end)} work hours")
        
        return ''.join(response_parts)
        
    except Exception as e:
        return None


def parse_time(time_str: str) -> int:
    """Parse time string like '9:00' or '09:30' to minutes since midnight."""
    time_str = time_str.strip()
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])


def format_time(minutes: int) -> str:
    """Format minutes since midnight to HH:MM string."""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def extract_busy_times(text: str, participant: str, day: str, available_days: list) -> list:
    """Extract busy time intervals for a participant on a given day."""
    busy_times = []
    
    # Multiple patterns to match schedule descriptions
    # First, find the section for this participant
    
    # Pattern 1: "Name has the following meetings on Day: ..." or similar
    # Pattern 2: Lines containing participant name and time ranges
    
    # Find participant's schedule block
    # Look for various patterns
    
    lines = text.split('\n')
    in_participant_section = False
    participant_lines = []
    
    for line in lines:
        if participant in line and ('busy' in line.lower() or 'meeting' in line.lower() or 'schedule' in line.lower() or 'existing' in line.lower() or ':' in line):
            in_participant_section = True
            participant_lines.append(line)
            continue
        if in_participant_section:
            # Check if we've hit another participant or section
            is_other_participant = False
            # Check if line starts with a dash/bullet and contains times
            stripped = line.strip()
            if stripped.startswith('-') or stripped.startswith('•') or stripped.startswith('*'):
                participant_lines.append(line)
            elif any(p in line for p in ['has no meetings', 'has the following', 'is busy', 'no busy', 'does not have']):
                # This might be another participant's section
                in_participant_section = False
            elif stripped == '':
                in_participant_section = False
            else:
                participant_lines.append(line)
    
    # Now also try to find the participant's schedule in a more structured way
    # Look for "Participant ..." sections
    
    # Try several regex patterns to find busy times
    
    # For multi-day scenarios, we need to find day-specific info
    if len(available_days) > 1:
        # Look for day-specific patterns
        busy_times = extract_busy_for_day(text, participant, day)
    else:
        # Single day - all times belong to that day
        busy_times = extract_all_busy_times_for_participant(text, participant)
    
    return busy_times


def extract_busy_for_day(text: str, participant: str, day: str) -> list:
    """Extract busy times for a participant on a specific day in multi-day scenarios."""
    busy_times = []
    
    # Find the participant's section
    # Patterns like:
    # "Name:\n  Monday: 10:00 to 11:00, ...\n  Tuesday: ..."
    # "Name has the following meetings on Monday: 10:00 to 11:00 ..."
    # "Name:\n  Monday:\n    - 10:00 to 11:00\n    - ..."
    
    # Strategy: find participant name, then find the day, then extract times
    
    # First, isolate the participant's block
    participant_block = get_participant_block(text, participant)
    if not participant_block:
        return busy_times
    
    # Now find the day within the participant's block
    day_pattern = re.compile(rf'{day}\s*[:\-]?\s*(.*?)(?=(?:Monday|Tuesday|Wednesday|Thursday|Friday)\s*[:\-]|$)', re.DOTALL | re.IGNORECASE)
    day_match = day_pattern.search(participant_block)
    
    if day_match:
        day_text = day_match.group(0)
        # Also check for "no meetings" or "free"
        if re.search(r'no meetings|free|no busy|no existing', day_text, re.IGNORECASE):
            return []
        busy_times = find_time_ranges(day_text)
    else:
        # Check if "no meetings" for this day
        if re.search(rf'{day}.*?(?:no meetings|free|no busy)', participant_block, re.IGNORECASE):
            return []
    
    return busy_times


def extract_all_busy_times_for_participant(text: str, participant: str) -> list:
    """Extract all busy times for a participant (single day scenario)."""
    participant_block = get_participant_block(text, participant)
    if not participant_block:
        return []
    
    # Check for "no meetings" or "free all day"
    if re.search(r'no meetings|free all day|no busy|no existing|does not have any', participant_block, re.IGNORECASE):
        return []
    
    return find_time_ranges(participant_block)


def get_participant_block(text: str, participant: str) -> str:
    """Get the text block describing a participant's schedule."""
    lines = text.split('\n')
    
    # Find lines that mention this participant
    start_idx = None
    for i, line in enumerate(lines):
        if participant in line:
            start_idx = i
            break
    
    if start_idx is None:
        return ""
    
    # Collect lines until we hit another participant or end of schedules
    # We need to know all participant names to detect boundaries
    # Extract names from the text
    block_lines = [lines[start_idx]]
    
    for i in range(start_idx + 1, len(lines)):
        line = lines[i].strip()
        # Check if this line starts a new participant section
        # Usually indicated by a name followed by colon or "has"
        if line and not line.startswith('-') and not line.startswith('•') and not line.startswith('*'):
            # Check if it contains another person's name pattern (capitalized word followed by schedule info)
            if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z])?.*?(?:has|:|is busy|schedule)', line):
                # Check it's not still about our participant
                if participant not in line:
                    break
        block_lines.append(lines[i])
    
    return '\n'.join(block_lines)


def find_time_ranges(text: str) -> list:
    """Find all time ranges in a text block. Returns list of (start_minutes, end_minutes)."""
    ranges = []
    
    # Pattern: HH:MM to HH:MM or HH:MM - HH:MM
    pattern = re.compile(r'(\d{1,2}:\d{2})\s*(?:to|-)\s*(\d{1,2}:\d{2})')
    
    for match in pattern.finditer(text):
        start = parse_time(match.group(1))
        end = parse_time(match.group(2))
        if start < end:
            ranges.append((start, end))
    
    return sorted(ranges)


def extract_preferences(text: str, participants: list) -> dict:
    """Extract scheduling preferences for participants."""
    preferences = {}
    
    for participant in participants:
        prefs = {}
        
        # "Name prefers not to have meetings after HH:MM"
        after_match = re.search(rf'{participant}.*?(?:prefers?|would prefer|likes?).*?not.*?(?:meet|meetings?).*?after\s+(\d{{1,2}}:\d{{2}})', text, re.IGNORECASE)
        if after_match:
            prefs['not_after'] = parse_time(after_match.group(1))
        
        # "Name prefers not to have meetings before HH:MM"
        before_match = re.search(rf'{participant}.*?(?:prefers?|would prefer|likes?).*?not.*?(?:meet|meetings?).*?before\s+(\d{{1,2}}:\d{{2}})', text, re.IGNORECASE)
        if before_match:
            prefs['not_before'] = parse_time(before_match.group(1))
        
        # "Name prefers not to meet on Day"
        day_match = re.search(rf'{participant}.*?(?:prefers?|would prefer|likes?).*?not.*?(?:meet|meetings?).*?on\s+(Monday|Tuesday|Wednesday|Thursday|Friday)', text, re.IGNORECASE)
        if day_match:
            prefs['avoid_day'] = day_match.group(1)
        
        # "Name cannot meet on Day" - this is a hard constraint
        cannot_match = re.search(rf'{participant}.*?(?:cannot|can\'t|is unable to).*?(?:meet|attend|make it).*?on\s+(Monday|Tuesday|Wednesday|Thursday|Friday)', text, re.IGNORECASE)
        if cannot_match:
            prefs['cannot_day'] = cannot_match.group(1)
        
        # Also check: "Name prefers to have the meeting in the morning/afternoon"
        morning_match = re.search(rf'{participant}.*?(?:prefers?|would prefer).*?(?:morning|earlier)', text, re.IGNORECASE)
        if morning_match:
            prefs['prefer_morning'] = True
        
        afternoon_match = re.search(rf'{participant}.*?(?:prefers?|would prefer).*?(?:afternoon|later)', text, re.IGNORECASE)
        if afternoon_match:
            prefs['prefer_afternoon'] = True
        
        # "the group prefers the earliest"
        if 'earliest' in text.lower():
            prefs['prefer_earliest'] = True
        
        if prefs:
            preferences[participant] = prefs
    
    # Check for group-level preferences
    if 'earliest' in text.lower():
        preferences['_group'] = {'prefer_earliest': True}
    
    return preferences


def find_meeting_slot(participants, schedules, available_days, work_start, work_end, duration, preferences) -> tuple:
    """Find the earliest meeting slot that works for all participants."""
    
    # Determine day ordering based on preferences
    # Hard constraints: cannot meet on certain days
    cannot_days = set()
    avoid_days = set()
    
    for participant, prefs in preferences.items():
        if participant == '_group':
            continue
        if 'cannot_day' in prefs:
            cannot_days.add(prefs['cannot_day'])
        if 'avoid_day' in prefs:
            avoid_days.add(prefs['avoid_day'])
    
    # Filter out days participants cannot meet
    filtered_days = [d for d in available_days if d not in cannot_days]
    
    # Sort: prefer days not in avoid_days first, then by original order
    preferred_days = [d for d in filtered_days if d not in avoid_days]
    non_preferred_days = [d for d in filtered_days if d in avoid_days]
    
    day_order = preferred_days + non_preferred_days
    
    if not day_order:
        day_order = filtered_days if filtered_days else available_days
    
    # Time preference constraints
    time_not_after = {}
    time_not_before = {}
    
    for participant, prefs in preferences.items():
        if participant == '_group':
            continue
        if 'not_after' in prefs:
            time_not_after[participant] = prefs['not_after']
        if 'not_before' in prefs:
            time_not_before[participant] = prefs['not_before']
    
    # For each day, find available slots
    for day in day_order:
        # Collect all busy intervals for this day across all participants
        all_busy = []
        for participant in participants:
            if day in schedules[participant]:
                all_busy.extend(schedules[participant][day])
        
        # Sort busy intervals
        all_busy.sort()
        
        # Merge overlapping intervals
        merged = merge_intervals(all_busy)
        
        # Find free slots within work hours
        free_slots = find_free_slots(merged, work_start, work_end)
        
        # Check each free slot for a window of sufficient duration
        for slot_start, slot_end in free_slots:
            if slot_end - slot_start >= duration:
                # Try to place meeting at the start of this free slot
                meeting_start = slot_start
                meeting_end = meeting_start + duration
                
                # Check time preferences
                if satisfies_time_preferences(meeting_start, meeting_end, time_not_after, time_not_before):
                    # Verify against all individual schedules
                    if verify_no_conflicts(participants, schedules, day, meeting_start, meeting_end):
                        return (day, meeting_start, meeting_end)
                
                # If the earliest start doesn't satisfy preferences, try sliding
                # But first check if any position in this slot works
                step = 30  # 30-minute increments
                t = slot_start
                while t + duration <= slot_end:
                    if satisfies_time_preferences(t, t + duration, time_not_after, time_not_before):
                        if verify_no_conflicts(participants, schedules, day, t, t + duration):
                            return (day, t, t + duration)
                    t += step
    
    # If preferences couldn't be satisfied, try without time preferences
    for day in day_order:
        all_busy = []
        for participant in participants:
            if day in schedules[participant]:
                all_busy.extend(schedules[participant][day])
        
        all_busy.sort()
        merged = merge_intervals(all_busy)
        free_slots = find_free_slots(merged, work_start, work_end)
        
        for slot_start, slot_end in free_slots:
            t = slot_start
            step = 30
            while t + duration <= slot_end:
                if verify_no_conflicts(participants, schedules, day, t, t + duration):
                    return (day, t, t + duration)
                t += step
    
    # If still nothing found with avoid_days excluded, try avoid_days
    for day in non_preferred_days:
        all_busy = []
        for participant in participants:
            if day in schedules[participant]:
                all_busy.extend(schedules[participant][day])
        
        all_busy.sort()
        merged = merge_intervals(all_busy)
        free_slots = find_free_slots(merged, work_start, work_end)
        
        for slot_start, slot_end in free_slots:
            t = slot_start
            step = 30
            while t + duration <= slot_end:
                if verify_no_conflicts(participants, schedules, day, t, t + duration):
                    return (day, t, t + duration)
                t += step
    
    return None


def satisfies_time_preferences(start, end, not_after, not_before):
    """Check if meeting time satisfies time preferences."""
    for participant, max_time in not_after.items():
        if end > max_time:
            return False
    for participant, min_time in not_before.items():
        if start < min_time:
            return False
    return True


def verify_no_conflicts(participants, schedules, day, meeting_start, meeting_end):
    """Verify that no participant has a conflict during the proposed meeting time."""
    for participant in participants:
        if day in schedules[participant]:
            for busy_start, busy_end in schedules[participant][day]:
                # Check for overlap
                if meeting_start < busy_end and meeting_end > busy_start:
                    return False
    return True


def merge_intervals(intervals):
    """Merge overlapping intervals."""
    if not intervals:
        return []
    
    sorted_intervals = sorted(intervals)
    merged = [sorted_intervals[0]]
    
    for start, end in sorted_intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    
    return merged


def find_free_slots(busy_intervals, work_start, work_end):
    """Find free time slots within work hours given busy intervals."""
    free = []
    current = work_start
    
    for busy_start, busy_end in busy_intervals:
        if busy_start > current:
            free.append((current, min(busy_start, work_end)))
        current = max(current, busy_end)
    
    if current < work_end:
        free.append((current, work_end))
    
    return free
