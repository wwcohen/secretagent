"""Auto-generated code-distilled implementation for select_and_format."""

import json
import re

def select_and_format(slots_text: str, strategy: str) -> str:
    # Try to extract JSON array from the text
    # The input might be a plain JSON array or it might be embedded in a longer text
    
    slots = None
    
    # First, try to parse the entire text as JSON
    try:
        parsed = json.loads(slots_text)
        if isinstance(parsed, list):
            slots = parsed
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If that didn't work, try to find a JSON array in the text
    if slots is None:
        # Look for JSON arrays in the text
        # Find all potential JSON array patterns
        matches = re.findall(r'\[[\s\S]*?\]', slots_text)
        for match in matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict) and 'day' in parsed[0]:
                    slots = parsed
                    break
            except (json.JSONDecodeError, ValueError):
                continue
    
    # If we still don't have slots, try to find them with a more aggressive pattern
    if slots is None:
        # Try to find individual slot patterns and reconstruct
        slot_pattern = re.findall(r'\{[^{}]*"day"[^{}]*"start"[^{}]*"end"[^{}]*\}', slots_text)
        if slot_pattern:
            combined = '[' + ','.join(slot_pattern) + ']'
            try:
                slots = json.loads(combined)
            except (json.JSONDecodeError, ValueError):
                pass
    
    if slots is None or len(slots) == 0:
        return None
    
    # Validate that slots have the required fields
    valid_slots = []
    for slot in slots:
        if isinstance(slot, dict) and 'day' in slot and 'start' in slot and 'end' in slot:
            valid_slots.append(slot)
    
    if not valid_slots:
        return None
    
    # Define day ordering
    day_order = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    # Sort slots by day and then by start time
    def sort_key(slot):
        day_idx = day_order.get(slot['day'], 99)
        start = slot['start']
        return (day_idx, start)
    
    valid_slots.sort(key=sort_key)
    
    if strategy == 'earliest':
        selected = valid_slots[0]
    elif strategy == 'latest':
        selected = valid_slots[-1]
    else:
        return None
    
    return f"Here is the proposed time: {selected['day']}, {selected['start']} - {selected['end']}"
