"""Auto-generated code-distilled implementation for parse_meeting_info."""

import re
import json


def parse_meeting_info(text):
    try:
        # Extract my location and start time
        arrive_match = re.search(r"You arrive at (.+?) at (\d{1,2}:\d{2}\s*[AP]M)", text)
        if not arrive_match:
            return None
        my_location = arrive_match.group(1)
        my_start_time = arrive_match.group(2)

        # Extract travel times section
        travel_times = {}
        travel_pattern = re.findall(r"([A-Za-z\s']+?) to ([A-Za-z\s']+?): (\d+)\.", text)
        
        # Determine separator used: check if "->" appears in expected output context
        # We'll figure out from the travel lines themselves - they always use " to " in input
        # But output might use "->" or " to ". Look at examples more carefully.
        # The separator in output seems to match what's natural. Let me check patterns.
        
        for origin, dest, minutes in travel_pattern:
            origin = origin.strip()
            dest = dest.strip()
            travel_times[(origin, dest)] = int(minutes)

        # Extract friends
        friends = []
        friend_pattern = re.findall(
            r"(\b[A-Z][a-z]+)\b will be at (.+?) from (\d{1,2}:\d{2}\s*[AP]M) to (\d{1,2}:\d{2}\s*[AP]M)\.\s*You'd like to meet \1 for a minimum of (\d+) minutes\.",
            text
        )
        for name, location, avail_from, avail_to, duration in friend_pattern:
            friend = {
                "name": name,
                "location": location.strip(),
                "available_from": avail_from,
                "available_to": avail_to,
                "duration_minutes": int(duration)
            }
            friends.append(friend)

        # Build travel_times dict for output - preserve order from input
        travel_dict = {}
        # Determine separator: use "->" as default, but check if text after CONSTRAINTS 
        # or the overall output style. Looking at examples, the separator varies.
        # Use "->" as the separator for the keys
        separator = "->"
        
        for (origin, dest), minutes in travel_times.items():
            key = f"{origin}{separator}{dest}"
            travel_dict[key] = minutes

        result = {
            "my_location": my_location,
            "my_start_time": my_start_time,
            "friends": friends,
            "travel_times": travel_dict
        }

        # Check if "SOLUTION:" prefix is expected (if text ends with instruction about it)
        prefix = ""
        if "Your response should start with 'SOLUTION:'." in text or \
           "Your response should start with 'SOLUTION:'" in text:
            # Check if we should add prefix based on example 3
            prefix = "SOLUTION:\n"

        json_str = json.dumps(result)
        
        # Check if the output might need " to " separator instead of "->"
        # by looking at example patterns - some use " to ", rebuild if needed
        # Actually looking more carefully, most use "->". Let's keep "->".
        
        return prefix + json_str if prefix else json_str

    except Exception:
        return None
