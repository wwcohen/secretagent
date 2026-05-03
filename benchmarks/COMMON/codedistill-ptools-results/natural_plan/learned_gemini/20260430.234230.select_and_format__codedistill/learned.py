"""Auto-generated code-distilled implementation for select_and_format."""

import json
import re

def select_and_format(text, preference='earliest'):
    """
    Extracts the chosen time slot from the provided problem text or JSON string,
    and formats it according to the required output format.
    
    Returns None if a valid JSON array of slot dictionaries cannot be found.
    """
    def extract_json_lists(t):
        """
        Robustly extracts all valid JSON lists from a given string, 
        handling nested structures and escaped quotes without relying on regex boundaries.
        """
        results = []
        start_idx = t.find('[')
        while start_idx != -1:
            depth = 0
            in_string = False
            escape = False
            for i in range(start_idx, len(t)):
                c = t[i]
                if not escape:
                    if c == '"':
                        in_string = not in_string
                    elif not in_string:
                        if c == '[':
                            depth += 1
                        elif c == ']':
                            depth -= 1
                            if depth == 0:
                                json_str = t[start_idx:i+1]
                                try:
                                    data = json.loads(json_str)
                                    if isinstance(data, list):
                                        results.append(data)
                                except json.JSONDecodeError:
                                    pass
                                break
                
                # Toggle escape for the next character if we see a backslash
                if c == '\\' and not escape:
                    escape = True
                else:
                    escape = False
                    
            start_idx = t.find('[', start_idx + 1)
        return results

    # Get all parsed lists of structures from the input
    results = extract_json_lists(text)
    
    valid_lists = []
    # Filter for lists that actually contain slot dictionaries
    for data in results:
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict) and 'day' in data[0] and 'start' in data[0] and 'end' in data[0]:
                valid_lists.append(data)
                
    if valid_lists:
        # Take the last valid list found, assuming it's the final answer from a CoT reasoning trace
        data = valid_lists[-1]
        
        # Sort the slots chronologically to respect the 'earliest' or 'latest' preference
        DAYS = {
            "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4,
            "Friday": 5, "Saturday": 6, "Sunday": 7
        }
        
        def slot_key(s):
            day = s.get('day', '')
            start = s.get('start', '24:00')
            parts = start.split(':')
            if len(parts) == 2:
                try:
                    # Normalize time sorting (e.g. "9:00" vs "10:00")
                    start = f"{int(parts[0]):02d}:{parts[1]}"
                except ValueError:
                    pass
            return (DAYS.get(day, 8), start)
            
        data.sort(key=slot_key)
        
        if preference == 'latest':
            slot = data[-1]
        else:
            # Default to earliest
            slot = data[0]
            
        return f"Here is the proposed time: {slot['day']}, {slot['start']} - {slot['end']}"
        
    return None
