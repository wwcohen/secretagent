"""Auto-generated code-distilled implementation for parse_meeting_info."""

import re
import json


def parse_meeting_info(text):
    try:
        # Extract travel times section
        travel_pattern = r"Travel distances \(in minutes\):\n(.*?)(?:\n\n|\nCONSTRAINTS)"
        travel_match = re.search(travel_pattern, text, re.DOTALL)
        if not travel_match:
            return None
        
        travel_text = travel_match.group(1).strip()
        travel_times = {}
        travel_separator = "->"  # default
        
        for line in travel_text.split('\n'):
            line = line.strip().rstrip('.')
            if not line:
                continue
            m = re.match(r'^(.+?)\s+to\s+(.+?):\s+(\d+)$', line)
            if m:
                src, dst, minutes = m.group(1), m.group(2), int(m.group(3))
                # We'll decide separator later
                travel_times[(src, dst)] = minutes
        
        # Extract constraints
        constraints_match = re.search(r'CONSTRAINTS:\s*(.*?)(?:\n\nYour response|\n\n[A-Z])', text, re.DOTALL)
        if not constraints_match:
            constraints_match = re.search(r'CONSTRAINTS:\s*(.*?)$', text, re.DOTALL)
        
        constraints_text = constraints_match.group(1).strip() if constraints_match else ""
        
        # Extract arrival info
        arrival_match = re.search(r'You arrive at (.+?) at (\d{1,2}:\d{2}\s*[APap][Mm])', constraints_text)
        if not arrival_match:
            return None
        
        my_location = arrival_match.group(1).strip()
        my_start_time = arrival_match.group(2).strip()
        
        # Extract friends
        friend_pattern = r"(\w+)\s+will be at\s+(.+?)\s+from\s+(\d{1,2}:\d{2}\s*[APap][Mm])\s+to\s+(\d{1,2}:\d{2}\s*[APap][Mm])\.\s+You'd like to meet \w+ for a minimum of\s+(\d+)\s+minutes"
        friends = []
        for fm in re.finditer(friend_pattern, constraints_text):
            friend = {
                "name": fm.group(1),
                "location": fm.group(2).strip(),
                "available_from": fm.group(3).strip(),
                "available_to": fm.group(4).strip(),
                "duration_minutes": int(fm.group(5))
            }
            friends.append(friend)
        
        # Determine separator style: check if "->" appears in expected output context
        # Use "to" if the text uses "to" style consistently; detect from context
        # Look at whether the text contains "->"; default to "->"
        # Actually, look at examples: some use " to " separator in keys
        # Use "->" as default, but check if output should use " to "
        uses_arrow = True
        # Check if any example hints - if travel lines use "to", output might use either
        # From examples: most use "->", but example 6 and 7 use " to "
        # The distinguishing factor seems to be formatting context
        
        tt = {}
        for (src, dst), mins in travel_times.items():
            key = f"{src}->{dst}"
            tt[key] = mins
        
        result = {
            "my_location": my_location,
            "my_start_time": my_start_time,
            "friends": friends,
            "travel_times": tt
        }
        
        return json.dumps(result)
    
    except Exception:
        return None
