"""Auto-generated code-distilled implementation for parse_trip_constraints."""

import re
import json
from collections import OrderedDict

def parse_trip_constraints(text):
    try:
        # Extract total days
        total_days_match = re.search(r'for (\d+) days in total', text)
        if not total_days_match:
            return None
        total_days = int(total_days_match.group(1))
        
        # Extract cities and their durations - find all mentions of city+days
        # Patterns: "stay in X for N days", "spend N days in X", "visit X for N days"
        city_patterns = [
            r'(?:plan to stay|stay) in ([A-Z][a-zA-Zéèêëàâäùûüôöîïç\s]+?) for (\d+) days',
            r'(?:want to spend|spend) (\d+) days in ([A-Z][a-zA-Zéèêëàâäùûüôöîïç\s]+?)(?:\.|,|\s)',
            r'(?:would like to visit|visit) ([A-Z][a-zA-Zéèêëàâäùûüôöîïç\s]+?) for (\d+) days',
        ]
        
        cities = OrderedDict()
        city_positions = {}
        
        for pattern in city_patterns:
            for match in re.finditer(pattern, text):
                groups = match.groups()
                if pattern == city_patterns[1]:  # "spend N days in City"
                    days, city = int(groups[0]), groups[1].strip()
                else:
                    city, days = groups[0].strip(), int(groups[1])
                
                pos = match.start()
                if city not in city_positions or pos < city_positions[city]:
                    city_positions[city] = pos
                cities[city] = days
        
        # Sort cities by first appearance position
        sorted_cities = OrderedDict(sorted(cities.items(), key=lambda x: city_positions[x[0]]))
        
        # Extract flights section
        flights_section_match = re.search(r'Here are the cities that have direct flights:\n(.*?)(?:\n\n|\n[A-Z]|$)', text, re.DOTALL)
        flights = OrderedDict()
        
        if flights_section_match:
            flights_text = flights_section_match.group(1).strip().rstrip('.')
            # Split by comma (but not within city names)
            flight_pairs = re.split(r',\s*', flights_text)
            
            for pair in flight_pairs:
                pair = pair.strip().rstrip('.')
                # "X and Y" (bidirectional) or "from X to Y" (bidirectional based on examples)
                from_to = re.match(r'from\s+(.+?)\s+to\s+(.+)', pair)
                and_match = re.match(r'(.+?)\s+and\s+(.+)', pair)
                
                if from_to:
                    c1, c2 = from_to.group(1).strip(), from_to.group(2).strip()
                elif and_match:
                    c1, c2 = and_match.group(1).strip(), and_match.group(2).strip()
                else:
                    continue
                
                if c1 not in flights:
                    flights[c1] = []
                if c2 not in flights[c1]:
                    flights[c1].append(c2)
                if c2 not in flights:
                    flights[c2] = []
                if c1 not in flights[c2]:
                    flights[c2].append(c1)
        
        # Extract time windows
        time_windows = []
        tw_patterns = [
            r'(?:attend a \w+ in|attend in) ([A-Z][a-zA-Zéèêëàâäùûüôöîïç\s]+?) between day (\d+) and day (\d+)',
            r'[Ff]rom day (\d+) to day (\d+),.*?(?:in|attend in) ([A-Z][a-zA-Zéèêëàâäùûüôöîïç\s]+?)(?:\.|$)',
        ]
        
        for match in re.finditer(tw_patterns[0], text):
            city, earliest, latest = match.group(1).strip(), int(match.group(2)), int(match.group(3))
            time_windows.append({"city": city, "earliest_day": earliest, "latest_day": latest})
        
        for match in re.finditer(tw_patterns[1], text):
            earliest, latest, city = int(match.group(1)), int(match.group(2)), match.group(3).strip()
            time_windows.append({"city": city, "earliest_day": earliest, "latest_day": latest})
        
        result = OrderedDict([
            ("total_days", total_days),
            ("cities", sorted_cities),
            ("flights", flights),
            ("time_windows", time_windows)
        ])
        
        return json.dumps(result)
    except Exception:
        return None
