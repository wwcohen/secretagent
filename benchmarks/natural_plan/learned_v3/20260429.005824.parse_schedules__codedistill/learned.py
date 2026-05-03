"""Auto-generated code-distilled implementation for parse_schedules."""

import re
import json

def parse_schedules(text):
    try:
        # Extract the TASK section
        task_match = re.search(r'TASK:\s*You need to schedule a meeting for (.+?) for (.+?) between the work hours of (\d+:\d+) to (\d+:\d+) on (.+?)\.', text)
        if not task_match:
            return None
        
        # Parse participants
        names_str = task_match.group(1)
        # Split by ", " and " and "
        # Handle "A, B, C and D" or "A and B"
        names_str = names_str.replace(' and ', ', ')
        participants = [n.strip() for n in names_str.split(',') if n.strip()]
        
        # Parse duration
        duration_str = task_match.group(2).strip()
        if 'half an hour' in duration_str:
            duration_minutes = 30
        elif 'one hour' in duration_str:
            duration_minutes = 60
        elif 'two hour' in duration_str:
            duration_minutes = 120
        elif 'hour and a half' in duration_str or '1.5 hour' in duration_str:
            duration_minutes = 90
        else:
            # Try to parse numeric
            m = re.search(r'(\d+)\s*minute', duration_str)
            if m:
                duration_minutes = int(m.group(1))
            else:
                duration_minutes = 30
        
        # Working hours
        working_hours = [task_match.group(3), task_match.group(4)]
        
        # Days
        days_str = task_match.group(5).strip()
        days_str = days_str.replace('either ', '')
        days_str = days_str.replace(' or ', ', ')
        days_str = days_str.replace(' and ', ', ')
        days = [d.strip() for d in days_str.split(',') if d.strip()]
        
        # Preference
        preference = None
        if re.search(r'earliest\s*(possible\s*)?time', text, re.IGNORECASE) or re.search(r'as early as possible', text, re.IGNORECASE) or re.search(r'prefer.*earliest', text, re.IGNORECASE) or re.search(r'earliest\s*slot', text, re.IGNORECASE):
            preference = "earliest"
        elif re.search(r'latest\s*(possible\s*)?time', text, re.IGNORECASE) or re.search(r'as late as possible', text, re.IGNORECASE) or re.search(r'prefer.*latest', text, re.IGNORECASE) or re.search(r'latest\s*slot', text, re.IGNORECASE):
            preference = "latest"
        
        # Parse schedules
        schedules = {}
        for participant in participants:
            schedules[participant] = {}
            for day in days:
                schedules[participant][day] = []
        
        # Find schedule descriptions for each participant
        # Pattern: "Name has mass/meetings/... on Day from H:MM to H:MM, ..." or "Name has no meetings..."
        # Look for lines like: "- Name: busy from ... on Day" or similar patterns
        
        # Try pattern: Name (is busy|has meetings|has existing) ...
        # Each participant's schedule line
        for participant in participants:
            # Find text about this participant's schedule
            # Pattern: participant name followed by schedule info
            pat = re.escape(participant) + r'[:\s]+(.*?)(?=\n\s*[-•]?\s*(?:' + '|'.join(re.escape(p) for p in participants if p != participant) + r')[\s:]|\nThe meeting|\nFind|\nNote|\nPlease|\Z)'
            
            block_match = re.search(pat, text, re.DOTALL)
            if not block_match:
                continue
            block = block_match.group(1)
            
            if re.search(r'(no (existing )?meetings|no scheduled|free all day|no busy|has no meeting|no prior|no event|not busy|has nothing)', block, re.IGNORECASE):
                if not re.search(r'\d{1,2}:\d{2}', block):
                    continue
            
            for day in days:
                # Find all time slots for this day
                # Pattern: "Day from H:MM to H:MM"
                day_times = re.findall(day + r'.*?(?=(?:' + '|'.join(d for d in days if d != day) + r')|$)', block, re.DOTALL)
                
                time_slots = []
                search_text = block
                # Find all "Day from H:MM to H:MM" patterns
                slot_pattern = re.findall(r'(?:' + re.escape(day) + r').*?(\d{1,2}:\d{2})\s*to\s*(\d{1,2}:\d{2})', search_text)
                
                # Also try pattern with "on Day" 
                all_times = re.findall(r'(\d{1,2}:\d{2})\s*to\s*(\d{1,2}:\d{2})(?:.*?' + re.escape(day) + r')|' + re.escape(day) + r'.*?(\d{1,2}:\d{2})\s*to\s*(\d{1,2}:\d{2})', search_text, re.DOTALL)
                
                for slot in slot_pattern:
                    time_slots.append([slot[0], slot[1]])
                
                schedules[participant][day] = time_slots
        
        # Better approach: parse the schedule section more carefully
        # Reset and re-parse
        schedules = {}
        for participant in participants:
            schedules[participant] = {day: [] for day in days}
        
        # Split by participant mentions in the schedule section
        sched_section = text[text.find('existing schedules'):]  if 'existing schedules' in text else text[text.find('schedules for'):]  if 'schedules for' in text else text
        
        lines = sched_section.split('\n')
        current_participant = None
        
        for line in lines:
            line_stripped = line.strip().lstrip('-•').strip()
            
            # Check if line starts with a participant name
            found_participant = None
            for p in participants:
                if line_stripped.startswith(p):
                    found_participant = p
                    break
            
            if found_participant:
                current_participant = found_participant
                rest = line_stripped[len(current_participant):]
                
                # Check for "no meetings" / "has no" / "is free"
                if re.search(r'(no (existing )?(meetings|scheduled|busy|event|commitment)|free all day|has nothing|not busy|no prior)', rest, re.IGNORECASE):
                    if not re.search(r'\d{1,2}:\d{2}', rest):
                        continue
                
                for day in days:
                    # Find all time ranges associated with this day
                    # Split by day references
                    day_pattern = re.escape(day) + r'[,:]?\s*(.*?)(?=' + '|'.join(re.escape(d) for d in days if d != day) + r'|$)'
                    day_matches = re.finditer(day_pattern, rest, re.DOTALL)
                    for dm in day_matches:
                        segment = dm.group(0)
                        times = re.findall(r'(\d{1,2}:\d{2})\s*(?:to|-)\s*(\d{1,2}:\d{2})', segment)
                        for t in times:
                            schedules[current_participant][day].append([t[0], t[1]])
        
        result = {
            "participants": participants,
            "duration_minutes": duration_minutes,
            "working_hours": working_hours,
            "days": days,
            "preference": preference,
            "schedules": schedules
        }
        
        return json.dumps(result)
    
    except Exception:
        return None
