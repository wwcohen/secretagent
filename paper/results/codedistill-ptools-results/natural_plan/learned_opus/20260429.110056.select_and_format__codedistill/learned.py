"""Auto-generated code-distilled implementation for select_and_format."""

import json
import re

def select_and_format(slots_str, preference):
    day_order = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    slots = []
    
    # Try to parse as JSON directly
    try:
        parsed = json.loads(slots_str)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and 'day' in item and 'start' in item and 'end' in item:
                    slots.append(item)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If no slots found from direct JSON parse, try to find JSON arrays in the text
    if not slots:
        # Try to find JSON array patterns in the text
        json_array_pattern = re.findall(r'\[.*?\]', slots_str, re.DOTALL)
        for match in json_array_pattern:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and 'day' in item and 'start' in item and 'end' in item:
                            slots.append(item)
            except (json.JSONDecodeError, ValueError):
                continue
    
    # If still no slots, try to extract from text patterns like "Monday, HH:MM - HH:MM"
    if not slots:
        day_names = '|'.join(day_order.keys())
        pattern = rf'({day_names}),?\s+(\d{{1,2}}:\d{{2}})\s*-\s*(\d{{1,2}}:\d{{2}})'
        matches = re.findall(pattern, slots_str)
        for match in matches:
            slots.append({'day': match[0], 'start': match[1], 'end': match[2]})
    
    # If still no slots, try to find "start": "HH:MM" patterns loosely
    if not slots:
        # Look for time slot mentions like "10:00 - 10:30" or "10:00 to 10:30" with day context
        day_names = list(day_order.keys())
        for day in day_names:
            if day in slots_str:
                time_pattern = r'(\d{1,2}:\d{2})\s*[-–to]+\s*(\d{1,2}:\d{2})'
                time_matches = re.findall(time_pattern, slots_str)
                for tm in time_matches:
                    slots.append({'day': day, 'start': tm[0], 'end': tm[1]})
                break
    
    if not slots:
        return None
    
    def time_to_minutes(t):
        parts = t.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    
    def slot_sort_key(slot):
        return (day_order.get(slot['day'], 99), time_to_minutes(slot['start']))
    
    if preference == 'earliest':
        selected = min(slots, key=slot_sort_key)
    elif preference == 'latest':
        selected = max(slots, key=slot_sort_key)
    else:
        selected = min(slots, key=slot_sort_key)
    
    day = selected['day']
    start = selected['start']
    end = selected['end']
    
    return f'Here is the proposed time: {day}, {start} - {end}'
