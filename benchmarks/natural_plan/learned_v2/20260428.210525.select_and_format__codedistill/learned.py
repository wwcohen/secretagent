"""Auto-generated code-distilled implementation for select_and_format."""

import json
import re

def select_and_format(input_str, preference):
    slots = None
    
    # Try to parse as JSON directly
    try:
        parsed = json.loads(input_str.strip())
        if isinstance(parsed, list):
            slots = parsed
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If not pure JSON, try to find JSON arrays in the text
    if slots is None:
        # Try to find JSON array patterns in the text
        json_pattern = re.findall(r'\[.*?\]', input_str, re.DOTALL)
        for match in json_pattern:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict) and 'day' in parsed[0]:
                    slots = parsed
                    break
            except (json.JSONDecodeError, ValueError):
                continue
    
    # If still no slots, try to extract from reasoning text
    if slots is None:
        # Look for slot patterns like "day, HH:MM - HH:MM" or "day: HH:MM-HH:MM"
        # Try to find the final computed slots mentioned in the text
        # Look for patterns like "Monday, 12:00 - 12:30" or "slot 10:30-11:00" etc.
        # Extract all mentioned day + time range patterns
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Find lines that mention "slot" or "available" with day and times, or final conclusion
        # Look for patterns like: "So slot: day "Monday", start "12:00", end "12:30""
        slot_pattern = re.findall(r'[Ss]lot[s]?[:\s]+(\w+day)[,\s]+(\d{1,2}:\d{2})\s*[-–to]+\s*(\d{1,2}:\d{2})', input_str)
        
        if not slot_pattern:
            # Try: "Monday has slots: 10:30-11:00, 15:00-15:30"
            for day in day_names:
                day_slots = re.findall(day + r'.*?slots?[:\s]+((?:\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}[,\s]*)+)', input_str)
                for match in day_slots:
                    times = re.findall(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', match)
                    for start, end in times:
                        slot_pattern.append((day, start, end))
        
        if not slot_pattern:
            # Try any "day HH:MM-HH:MM" or "day, HH:MM - HH:MM"
            for day in day_names:
                times = re.findall(day + r'[,:\s]+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', input_str)
                for start, end in times:
                    slot_pattern.append((day, start, end))
        
        if slot_pattern:
            slots = [{'day': d, 'start': s.zfill(5), 'end': e.zfill(5)} for d, s, e in slot_pattern]
    
    if not slots:
        return None
    
    day_order = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
    
    slots.sort(key=lambda s: (day_order.get(s['day'], 99), s['start']))
    
    if preference == 'earliest':
        selected = slots[0]
    elif preference == 'latest':
        selected = slots[-1]
    else:
        selected = slots[0]
    
    return f"Here is the proposed time: {selected['day']}, {selected['start']} - {selected['end']}"
