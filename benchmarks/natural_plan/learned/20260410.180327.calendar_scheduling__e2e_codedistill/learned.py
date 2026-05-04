"""Auto-generated end-to-end implementation for calendar_scheduling."""

import re
from datetime import datetime, timedelta


def calendar_scheduling(prompt):
    parsed = parse_input(prompt)
    if parsed is None:
        return None
    result = solve(parsed)
    if result is None:
        return None
    return format_output(result)


def parse_input(prompt):
    try:
        info = {}
        
        # Extract participants
        task_match = re.search(r'TASK:.*?schedule a meeting for (.+?) for', prompt)
        if not task_match:
            return None
        names_str = task_match.group(1)
        names = re.split(r',\s*|\s+and\s+', names_str)
        names = [n.strip() for n in names if n.strip()]
        info['participants'] = names
        
        # Extract duration
        dur_match = re.search(r'for (one hour|half an hour|one and a half hours?|two hours?|(\d+) minutes?)', prompt)
        if not dur_match:
            return None
        dur_str = dur_match.group(1)
        if dur_str == 'one hour':
            info['duration'] = 60
        elif dur_str == 'half an hour':
            info['duration'] = 30
        elif 'one and a half' in dur_str:
            info['duration'] = 90
        elif 'two hour' in dur_str:
            info['duration'] = 120
        else:
            info['duration'] = int(dur_match.group(2))
        
        # Extract work hours
        wh_match = re.search(r'work hours of (\d+:\d+) to (\d+:\d+)', prompt)
        if not wh_match:
            return None
        info['work_start'] = time_to_minutes(wh_match.group(1))
        info['work_end'] = time_to_minutes(wh_match.group(2))
        
        # Extract days
        days_match = re.search(r'on ((?:either )?(?:Monday|Tuesday|Wednesday|Thursday|Friday)(?:(?:,\s*| or )(?:Monday|Tuesday|Wednesday|Thursday|Friday))*)', prompt)
        if not days_match:
            return None
        days_str = days_match.group(1)
        days_str = days_str.replace('either ', '')
        day_names = re.findall(r'(Monday|Tuesday|Wednesday|Thursday|Friday)', days_str)
        info['days'] = day_names
        
        # Extract schedules
        schedules_section = prompt.split('schedules for everyone during the day')[0] if 'during the day' in prompt else prompt
        
        info['busy'] = {}
        for name in names:
            info['busy'][name] = {}
            for day in day_names:
                info['busy'][name][day] = []
        
        # Parse busy times for each participant
        # Find the schedules section
        sched_start = prompt.find('Here are the existing schedules')
        if sched_start == -1:
            return None
        
        # Find where constraints/preferences or "Find a time" starts
        find_time_pos = prompt.find('Find a time that works')
        sched_section = prompt[sched_start:find_time_pos] if find_time_pos != -1 else prompt[sched_start:]
        
        # Split by participant lines
        for name in names:
            # Handle various phrasings for free/no meetings
            free_patterns = [
                rf'{re.escape(name)} is free the entire (?:day|week)',
                rf'{re.escape(name)}\'s calendar is wide open the entire (?:day|week)',
                rf'{re.escape(name)}has no meetings the whole (?:day|week)',
                rf'{re.escape(name)} has no meetings the whole (?:day|week)',
            ]
            is_free = False
            for fp in free_patterns:
                if re.search(fp, sched_section):
                    is_free = True
                    break
            
            if is_free:
                continue
            
            # Find this person's schedule line(s)
            # Pattern: Name (is busy|has blocked their calendar|has meetings) on Day during times, Day during times;
            pattern = rf'{re.escape(name)} (?:is busy|has blocked their calendar|has meetings) on ([^;]+);'
            match = re.search(pattern, sched_section)
            if match:
                schedule_str = match.group(1)
                # Parse day segments
                # Split by day names while keeping the day name
                # Pattern: "Monday during ..., Tuesday during ..."
                day_segments = re.split(r'(?:,\s*)?(?=(Monday|Tuesday|Wednesday|Thursday|Friday) during)', schedule_str)
                
                # Better approach: find all day + times pairs
                day_time_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday) during ([\d:,\s to]+?)(?=(?:,\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday) during)|$)'
                day_matches = re.finditer(day_time_pattern, schedule_str)
                
                for dm in day_matches:
                    day = dm.group(1)
                    times_str = dm.group(2)
                    # Parse individual time ranges
                    time_ranges = re.findall(r'(\d+:\d+) to (\d+:\d+)', times_str)
                    for start_str, end_str in time_ranges:
                        start = time_to_minutes(start_str)
                        end = time_to_minutes(end_str)
                        if day in info['busy'][name]:
                            info['busy'][name][day].append((start, end))
        
        # Parse constraints and preferences
        info['hard_constraints'] = []  # (name, day, 'before'/'after'/'all', time)
        info['soft_preferences'] = []  # (name, day, 'before'/'after'/'all', time)
        info['earliest'] = False
        
        # Check for "earliest availability"
        if 'earlist availability' in prompt or 'earliest availability' in prompt:
            info['earliest'] = True
        
        # Find constraints section (between last schedule line and "Find a time")
        constraint_section = ''
        if find_time_pos != -1:
            # Look for text after the last semicolon of schedules but before "Find a time"
            last_semi = sched_section.rfind(';')
            if last_semi != -1:
                after_sched = prompt[sched_start + last_semi + 1:find_time_pos].strip()
                constraint_section = after_sched
            else:
                constraint_section = ''
        
        # Also check for constraints embedded in the text
        # Look between schedules end and "Find a time"
        lines_after = constraint_section.split('\n')
        constraint_text = ' '.join(l.strip() for l in lines_after if l.strip())
        
        # Parse hard constraints: "X can not meet on Day." or "X can not meet on Day before/after time."
        # Parse soft preferences: "X would like to avoid more meetings on Day." "X would rather not meet on Day." "X do not want to meet on Day."
        
        _parse_constraints(constraint_text, info, names)
        
        return info
    except Exception:
        return None


def _parse_constraints(text, info, names):
    if not text:
        return
    
    # Split into sentences roughly
    sentences = re.split(r'(?<=[.])\s*', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Check for "earliest availability"
        if 'earlist availability' in sentence or 'earliest availability' in sentence:
            info['earliest'] = True
            continue
        
        for name in names:
            # Hard constraints: "can not meet"
            # Soft preferences: "would like to avoid", "would rather not meet", "do not want to meet"
            
            hard_pattern = rf'{re.escape(name)} can not meet on (.+?)(?:\.|$)'
            soft_patterns = [
                rf'{re.escape(name)} would like to avoid more meetings on (.+?)(?:\.|$)',
                rf'{re.escape(name)} would rather not meet on (.+?)(?:\.|$)',
                rf'{re.escape(name)} do not want to meet on (.+?)(?:\.|$)',
            ]
            
            hard_match = re.search(hard_pattern, sentence)
            if hard_match:
                _parse_constraint_detail(hard_match.group(1), name, info, 'hard')
                continue
            
            for sp in soft_patterns:
                soft_match = re.search(sp, sentence)
                if soft_match:
                    _parse_constraint_detail(soft_match.group(1), name, info, 'soft')
                    break
    
    # Also handle "The group would like to meet at their earlist availability"
    if 'earlist availability' in text or 'earliest availability' in text:
        info['earliest'] = True
    
    # Handle "You would like to schedule the meeting at their earlist availability"
    if 'schedule the meeting at their earlist availability' in text:
        info['earliest'] = True


def _parse_constraint_detail(detail_str, name, info, constraint_type):
    detail_str = detail_str.strip().rstrip('.')
    
    # Could be: "Monday" or "Monday before 13:00" or "Monday after 13:00" or "Monday. Tuesday after 14:00"
    # or "Monday. Tuesday" etc.
    
    # Split by ". " or just "." to handle multiple constraints
    parts = re.split(r'\.\s*', detail_str)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Check for "Day before/after time"
        ba_match = re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday)\s+(before|after)\s+(\d+:\d+)', part)
        if ba_match:
            day = ba_match.group(1)
            direction = ba_match.group(2)
            time_val = time_to_minutes(ba_match.group(3))
            constraint = (name, day, direction, time_val)
            if constraint_type == 'hard':
                info['hard_constraints'].append(constraint)
            else:
                info['soft_preferences'].append(constraint)
            continue
        
        # Check for just a day name
        day_match = re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday)$', part)
        if day_match:
            day = day_match.group(1)
            constraint = (name, day, 'all', None)
            if constraint_type == 'hard':
                info['hard_constraints'].append(constraint)
            else:
                info['soft_preferences'].append(constraint)
            continue


def time_to_minutes(time_str):
    h, m = time_str.split(':')
    return int(h) * 60 + int(m)


def minutes_to_time(minutes):
    h = minutes // 60
    m = minutes % 60
    return f'{h}:{m:02d}'


def solve(info):
    duration = info['duration']
    work_start = info['work_start']
    work_end = info['work_end']
    days = info['days']
    participants = info['participants']
    busy = info['busy']
    hard_constraints = info['hard_constraints']
    soft_preferences = info['soft_preferences']
    earliest = info['earliest']
    
    # Generate all possible slots (in 30-minute increments)
    all_slots = []
    for day in days:
        t = work_start
        while t + duration <= work_end:
            all_slots.append((day, t, t + duration))
            t += 30
    
    # Filter by busy times
    def is_free(day, start, end):
        for name in participants:
            if day in busy[name]:
                for bs, be in busy[name][day]:
                    if start < be and end > bs:
                        return False
        return True
    
    available_slots = [(d, s, e) for d, s, e in all_slots if is_free(d, s, e)]
    
    # Apply hard constraints
    def passes_hard(day, start, end):
        for name, cday, direction, time_val in hard_constraints:
            if direction == 'all' and day == cday:
                return False
            elif direction == 'before' and day == cday:
                if start < time_val:
                    return False
            elif direction == 'after' and day == cday:
                if end > time_val:
                    return False
        return True
    
    hard_filtered = [(d, s, e) for d, s, e in available_slots if passes_hard(d, s, e)]
    
    if not hard_filtered:
        return None
    
    # Apply soft preferences - try to find slots that satisfy all soft preferences
    def soft_score(day, start, end):
        score = 0
        for name, cday, direction, time_val in soft_preferences:
            if direction == 'all' and day == cday:
                score += 1
            elif direction == 'before' and day == cday:
                if start < time_val:
                    score += 1
            elif direction == 'after' and day == cday:
                if end > time_val:
                    score += 1
        return score
    
    # Sort: first by soft score (fewer violations better), then by day order, then by start time
    day_order = {d: i for i, d in enumerate(days)}
    
    if earliest:
        # Earliest availability - just sort by day then time, with soft as tiebreaker
        hard_filtered.sort(key=lambda x: (soft_score(x[0], x[1], x[2]), day_order[x[0]], x[1]))
    else:
        # Default: prefer slots with no soft violations, then earliest
        hard_filtered.sort(key=lambda x: (soft_score(x[0], x[1], x[2]), day_order[x[0]], x[1]))
    
    best = hard_filtered[0]
    return best


def format_output(result):
    day, start, end = result
    start_str = minutes_to_time(start)
    end_str = minutes_to_time(end)
    return f'Here is the proposed time: {day}, {start_str} - {end_str} '
