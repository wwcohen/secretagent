"""Auto-generated code-distilled implementation for parse_meeting_info."""

import re
import json


def parse_meeting_info(text):
    try:
        # Extract my location and start time
        # Pattern: "You arrive at <location> at <time>"
        arrive_match = re.search(r'You arrive at (.+?) at (\d{1,2}:\d{2}(?:AM|PM))', text)
        if not arrive_match:
            return None
        
        my_location = arrive_match.group(1)
        my_start_time_raw = arrive_match.group(2)
        
        # Format time: "9:00AM" -> "9:00 AM"
        def format_time(t):
            # Insert space before AM/PM if not already there
            t = re.sub(r'(\d)(AM|PM)', r'\1 \2', t)
            return t
        
        my_start_time = format_time(my_start_time_raw)
        
        # Extract travel times
        # Pattern: "<Location A> to <Location B>: <number>."
        travel_pattern = re.compile(r'^(.+?) to (.+?): (\d+)\.$', re.MULTILINE)
        travel_times = {}
        for match in travel_pattern.finditer(text):
            from_loc = match.group(1)
            to_loc = match.group(2)
            minutes = int(match.group(3))
            key = f"{from_loc}->{to_loc}"
            travel_times[key] = minutes
        
        # Extract friends info
        # Pattern: "<Name> will be at <Location> from <time> to <time>. You'd like to meet <Name> for a minimum of <number> minutes."
        # Need to handle the constraint section
        friends = []
        
        # Find all friend constraints
        # Pattern: "<Name> will be at <Location> from <starttime> to <endtime>."
        friend_pattern = re.compile(
            r'(\b[A-Z][a-z]+\b) will be at (.+?) from (\d{1,2}:\d{2}(?:AM|PM)) to (\d{1,2}:\d{2}(?:AM|PM))\.'
        )
        
        # Pattern for duration: "You'd like to meet <Name> for a minimum of <number> minutes."
        duration_pattern = re.compile(
            r"You'd like to meet (\b[A-Z][a-z]+\b) for a minimum of (\d+) minutes\."
        )
        
        # Build duration map
        duration_map = {}
        for match in duration_pattern.finditer(text):
            name = match.group(1)
            duration = int(match.group(2))
            duration_map[name] = duration
        
        for match in friend_pattern.finditer(text):
            name = match.group(1)
            location = match.group(2)
            available_from = format_time(match.group(3))
            available_to = format_time(match.group(4))
            duration = duration_map.get(name, 0)
            
            friends.append({
                "name": name,
                "location": location,
                "available_from": available_from,
                "available_to": available_to,
                "duration_minutes": duration
            })
        
        result = {
            "my_location": my_location,
            "my_start_time": my_start_time,
            "friends": friends,
            "travel_times": travel_times
        }
        
        # Determine formatting: use indented format if few enough entries or based on some heuristic
        # Looking at examples, some return compact JSON and some return indented
        # The indented ones seem to be for specific cases. Let's check:
        # Example with 1 friend and simple case can be either compact or indented
        # Let's just return compact JSON (most examples use compact)
        # Actually looking more carefully, the expected outputs vary. Let's just return json.dumps
        # and match the format. Most are compact, some are indented.
        # Since the function returns a string, let's use compact format (no extra spaces/newlines)
        # as that's the most common pattern.
        
        return json.dumps(result)
    
    except Exception:
        return None
