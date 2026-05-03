"""Auto-generated workflow-distilled implementation for calendar_scheduling.

Calls existing tools from ptools_calendar.
"""

from ptools_calendar import *

import re
from datetime import datetime, timedelta

def calendar_scheduling(prompt):
    """Pure-Python calendar scheduling that parses constraints and finds optimal meeting time."""
    try:
        return _solve_scheduling(prompt)
    except Exception:
        return None


def _parse_time(t_str):
    """Parse time string like '9:00' or '17:00' into minutes from midnight."""
    t_str = t_str.strip()
    parts = t_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])


def _format_time(minutes):
    """Format minutes from midnight into HH:MM string."""
    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}"


def _solve_scheduling(prompt):
    # Extract the task section
    # Find the last TASK: ... SOLUTION: pair (the actual task to solve)
    # The prompt contains example tasks and then the actual task
    
    # Split on "TASK:" and take the last one
    task_splits = prompt.split("TASK: ")
    if len(task_splits) < 2:
        return None
    
    last_task = task_splits[-1]
    
    # Extract meeting duration
    duration_minutes = None
    if "half an hour" in last_task or "half hour" in last_task:
        duration_minutes = 30
    elif "one hour" in last_task or "1 hour" in last_task:
        duration_minutes = 60
    elif "one and a half hour" in last_task or "1.5 hour" in last_task or "ninety minutes" in last_task:
        duration_minutes = 90
    elif "two hour" in last_task or "2 hour" in last_task:
        duration_minutes = 120
    else:
        dur_match = re.search(r'for (\d+) minutes', last_task)
        if dur_match:
            duration_minutes = int(dur_match.group(1))
        else:
            return None
    
    # Extract work hours
    work_match = re.search(r'between the work hours of (\d+:\d+) to (\d+:\d+)', last_task)
    if work_match:
        work_start = _parse_time(work_match.group(1))
        work_end = _parse_time(work_match.group(2))
    else:
        work_start = _parse_time("9:00")
        work_end = _parse_time("17:00")
    
    # Extract allowed days
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    days_match = re.search(r'on (?:either )?((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:(?:,\s*| or )(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))*)', last_task)
    if days_match:
        days_str = days_match.group(1)
        allowed_days = re.findall(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', days_str)
    else:
        # Check for single day
        single_day = re.search(r'on (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\.', last_task)
        if single_day:
            allowed_days = [single_day.group(1)]
        else:
            allowed_days = day_order[:5]
    
    # Sort allowed_days by day_order
    allowed_days = sorted(set(allowed_days), key=lambda d: day_order.index(d))
    
    # Extract participant names
    names_match = re.search(r'schedule a meeting for (.+?) for (?:half an hour|one hour|two hours|\d+ minutes|one and a half)', last_task)
    if not names_match:
        return None
    
    names_str = names_match.group(1)
    # Parse names: "A, B, C and D" or "A and B"
    names_str = names_str.replace(' and ', ', ')
    participants = [n.strip() for n in names_str.split(',') if n.strip()]
    
    # Extract schedules section
    schedule_section_match = re.search(r'Here are the existing schedules for everyone during the days?:\s*\n(.*?)(?:\n\n|\nFind|\n[A-Z][a-z]+ (?:do not|would|can not|prefer))', last_task, re.DOTALL)
    if not schedule_section_match:
        # Try broader match
        schedule_section_match = re.search(r'Here are the existing schedules for everyone during the days?:\s*\n(.*?)(?:\n\n)', last_task, re.DOTALL)
    
    if not schedule_section_match:
        # Try to get everything between schedules header and the constraints/solution
        schedule_section_match = re.search(r'Here are the existing schedules for everyone during the days?:\s*\n(.*)', last_task, re.DOTALL)
    
    if not schedule_section_match:
        return None
    
    schedule_text = schedule_section_match.group(1)
    
    # Parse each participant's schedule
    # Format: "Name has blocked their calendar on Monday during 9:00 to 10:30, ..."
    # or "Name has meetings on Monday during ..."
    # or "Name is busy on Monday during ..."
    # or "Name is free the entire day."
    # or "Namehas no meetings the whole week."
    
    blocked = {}  # {participant: {day: [(start, end), ...]}}
    for p in participants:
        blocked[p] = {d: [] for d in allowed_days}
    
    # Split schedule text by participant - each line starts with a participant name
    # Handle "Namehas" (no space) and "Name has" cases
    for p in participants:
        # Find the schedule line for this participant
        # Handle both "Name has" and "Namehas" (typo in data)
        pattern = re.escape(p) + r'\s*(?:has blocked their calendar|has meetings|is busy|has no meetings|is free)'
        p_match = re.search(pattern, schedule_text)
        if not p_match:
            continue
        
        # Get the text from this match to the next participant or end
        start_pos = p_match.start()
        # Find end - next participant name or end of schedule_text
        end_pos = len(schedule_text)
        for other_p in participants:
            if other_p == p:
                continue
            other_pattern = re.escape(other_p) + r'\s*(?:has|is)'
            other_match = re.search(other_pattern, schedule_text[start_pos + len(p):])
            if other_match:
                candidate_end = start_pos + len(p) + other_match.start()
                if candidate_end < end_pos:
                    end_pos = candidate_end
        
        p_schedule_text = schedule_text[start_pos:end_pos]
        
        if 'no meetings' in p_schedule_text or 'free the entire' in p_schedule_text or 'free all' in p_schedule_text:
            continue
        
        # Parse day-specific blocks
        # Pattern: "Monday during 9:00 to 10:30, 11:00 to 12:00, Tuesday during ..."
        # We need to find each day and its time blocks
        for day in day_order:
            day_pattern = day + r'\s+during\s+([\d:]+\s+to\s+[\d:]+(?:\s*,\s*[\d:]+\s+to\s+[\d:]+)*)'
            day_matches = re.finditer(day_pattern, p_schedule_text)
            for dm in day_matches:
                time_blocks_str = dm.group(1)
                time_pairs = re.findall(r'(\d+:\d+)\s+to\s+(\d+:\d+)', time_blocks_str)
                for start_t, end_t in time_pairs:
                    s = _parse_time(start_t)
                    e = _parse_time(end_t)
                    if day in blocked[p]:
                        blocked[p][day].append((s, e))
                    else:
                        blocked[p][day] = [(s, e)]
    
    # Parse constraints/preferences section
    # This comes after the schedule section, before "Find a time..."
    constraints_match = re.search(r';\s*\n\n(.*?)Find a time', last_task, re.DOTALL)
    if not constraints_match:
        constraints_match = re.search(r';\s*\n(.*?)Find a time', last_task, re.DOTALL)
    
    hard_constraints = {}  # {participant: {day: [(blocked_start, blocked_end), ...]}}
    soft_preferences = {}  # {participant: {day: [(avoid_start, avoid_end), ...]}}
    day_hard_avoid = {}    # {participant: set of days completely blocked}
    day_soft_avoid = {}    # {participant: set of days to avoid}
    
    for p in participants:
        hard_constraints[p] = {d: [] for d in allowed_days}
        soft_preferences[p] = {d: [] for d in allowed_days}
        day_hard_avoid[p] = set()
        day_soft_avoid[p] = set()
    
    if constraints_match:
        constraints_text = constraints_match.group(1).strip()
        
        # Parse constraints for each participant
        # Split by sentences (separated by '. ' or '.\n')
        # Types of constraints:
        # Hard: "X do not want to meet on Monday" / "X can not meet on Wednesday"
        # Soft: "X would like to avoid more meetings on Monday" / "X would rather not meet on Monday"
        # With time qualifiers: "after 14:30" / "before 11:00"
        
        # Process each sentence
        sentences = re.split(r'\.\s+', constraints_text.rstrip('.'))
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            
            # Determine which participant
            matched_participant = None
            for p in participants:
                if sent.startswith(p):
                    matched_participant = p
                    break
            
            if not matched_participant:
                # Try "The group"
                if sent.startswith("The group") or sent.startswith("You would like"):
                    # These are preference/meta constraints
                    if "earli" in sent.lower():
                        # "earliest availability" - prefer earliest
                        pass  # This is the default behavior
                    continue
                continue
            
            rest = sent[len(matched_participant):].strip()
            
            is_hard = False
            is_soft = False
            
            if 'do not want to meet' in rest or 'can not meet' in rest or "doesn't want" in rest or "cannot meet" in rest:
                is_hard = True
            elif 'would like to avoid' in rest or 'would rather not' in rest or 'prefers not' in rest or 'would prefer not' in rest:
                is_soft = True
            else:
                # Unknown constraint type, treat as soft
                is_soft = True
            
            # Extract days and time constraints from rest
            # Pattern: "on Monday after 14:30" or "on Monday" or "on Monday before 11:00"
            # Could also be: "on Monday. Tuesday. Wednesday" (multiple days separated by periods)
            # Or: "on Monday after 14:30. Tuesday. Wednesday"
            
            # First find the "on" part
            on_match = re.search(r'on\s+(.*)', rest)
            if not on_match:
                continue
            
            on_text = on_match.group(1).strip().rstrip('.')
            
            # Parse compound day specifications
            # Could be like "Monday after 14:30. Tuesday. Wednesday"
            # Or "Monday. Tuesday. Wednesday before 12:00"
            # Or just "Monday"
            # Split by '. ' to get individual day specs
            day_specs = re.split(r'\.\s*', on_text)
            
            for spec in day_specs:
                spec = spec.strip()
                if not spec:
                    continue
                
                # Extract day name
                day_match = re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', spec)
                if not day_match:
                    continue
                
                day_name = day_match.group(1)
                remainder = spec[len(day_name):].strip()
                
                if not remainder:
                    # Entire day constraint
                    if is_hard:
                        day_hard_avoid[matched_participant].add(day_name)
                    else:
                        day_soft_avoid[matched_participant].add(day_name)
                else:
                    # Time-qualified constraint
                    after_match = re.search(r'after\s+(\d+:\d+)', remainder)
                    before_match = re.search(r'before\s+(\d+:\d+)', remainder)
                    
                    if after_match:
                        t = _parse_time(after_match.group(1))
                        if is_hard:
                            hard_constraints[matched_participant].setdefault(day_name, []).append((t, work_end))
                        else:
                            soft_preferences[matched_participant].setdefault(day_name, []).append((t, work_end))
                    
                    if before_match:
                        t = _parse_time(before_match.group(1))
                        if is_hard:
                            hard_constraints[matched_participant].setdefault(day_name, []).append((work_start, t))
                        else:
                            soft_preferences[matched_participant].setdefault(day_name, []).append((work_start, t))
    
    # Check for "earliest availability" preference
    prefer_earliest = False
    if constraints_match:
        ct = constraints_match.group(1).strip().lower()
        if 'earli' in ct:
            prefer_earliest = True
    # Also check in the task text itself
    if 'earli' in last_task.lower():
        prefer_earliest = True
    
    # Now find available slots
    # For each allowed day, find time windows where all participants are free
    # and no hard constraints are violated
    
    def is_slot_free(day, slot_start, slot_end):
        """Check if a slot is free for all participants (schedule + hard constraints)."""
        for p in participants:
            # Check hard day avoidance
            if day in day_hard_avoid[p]:
                return False
            
            # Check schedule blocks
            for bs, be in blocked[p].get(day, []):
                if slot_start < be and slot_end > bs:
                    return False
            
            # Check hard time constraints
            for cs, ce in hard_constraints[p].get(day, []):
                if slot_start < ce and slot_end > cs:
                    return False
        
        return True
    
    def slot_soft_penalty(day, slot_start, slot_end):
        """Calculate soft preference penalty for a slot."""
        penalty = 0
        for p in participants:
            if day in day_soft_avoid[p]:
                penalty += 1
            for ps, pe in soft_preferences[p].get(day, []):
                if slot_start < pe and slot_end > ps:
                    penalty += 1
        return penalty
    
    # Generate all possible slots across all allowed days
    all_slots = []
    for day in allowed_days:
        t = work_start
        while t + duration_minutes <= work_end:
            if is_slot_free(day, t, t + duration_minutes):
                penalty = slot_soft_penalty(day, t, t + duration_minutes)
                day_idx = day_order.index(day)
                all_slots.append((penalty, day_idx, t, day, t + duration_minutes))
            t += 30  # Check every 30 minutes
    
    if not all_slots:
        return None
    
    # Sort by: penalty first, then day order, then time (earliest)
    if prefer_earliest:
        # When "earliest availability" is requested, prioritize by day then time, but still respect soft preferences
        # Actually, "earliest" means the first available slot chronologically
        # But we still need to consider soft preferences? Looking at the examples:
        # The "earliest" examples seem to just want chronologically first across days
        # But we should still avoid soft-preference slots if there's an equally early option
        # Let's sort primarily by (day_idx, time) and use penalty as tiebreaker
        all_slots.sort(key=lambda x: (x[1], x[2], x[0]))
    else:
        # When there are soft preferences but no "earliest" requirement,
        # minimize penalty first, then choose earliest
        all_slots.sort(key=lambda x: (x[0], x[1], x[2]))
    
    best = all_slots[0]
    _, _, start_time, day_name, end_time = best
    
    result = f"Here is the proposed time: {day_name}, {_format_time(start_time)} - {_format_time(end_time)} "
    return result
