"""Auto-generated code-distilled implementation for parse_trip_constraints."""

import re
import json

def parse_trip_constraints(text):
    if not text:
        return None

    # Total days
    m = re.search(r'for (\d+) days in total', text)
    if not m:
        return None
    total_days = int(m.group(1))

    # Cities
    city_matches = []
    
    # Match patterns for cities and days
    for m_city in re.finditer(r'(?:stay in|visit) ([A-Z][a-zA-Z]+) for (\d+) days', text):
        city_matches.append({
            'pos': m_city.start(),
            'city': m_city.group(1),
            'days': int(m_city.group(2))
        })
    for m_city in re.finditer(r'spend (\d+) days in ([A-Z][a-zA-Z]+)', text):
        city_matches.append({
            'pos': m_city.start(),
            'city': m_city.group(2),
            'days': int(m_city.group(1))
        })
    
    # Sort cities by appearance in the text
    city_matches.sort(key=lambda x: x['pos'])
    cities = {}
    for x in city_matches:
        cities[x['city']] = x['days']

    # Flights
    flights = {}
    flight_section_match = re.search(r'direct flights:\n(.*?)(?:\.\n|\n\n|$)', text, re.DOTALL)
    if flight_section_match:
        flight_text = flight_section_match.group(1)
        # Extract pairs connected by 'and' or 'to' (with optional 'from')
        for m_flight in re.finditer(r'(?:from\s+)?([A-Z][a-zA-Z]+)\s+(?:and|to)\s+([A-Z][a-zA-Z]+)', flight_text):
            c1, c2 = m_flight.group(1), m_flight.group(2)
            if c1 not in flights:
                flights[c1] = []
            if c2 not in flights:
                flights[c2] = []
            if c2 not in flights[c1]:
                flights[c1].append(c2)
            if c1 not in flights[c2]:
                flights[c2].append(c1)

    # Time windows
    tw_matches = []
    
    # Pattern 1: e.g., "in/at {City} between day {X} and day {Y}"
    for m_tw in re.finditer(r'(?:in|at) ([A-Z][a-zA-Z]+) between day (\d+) and day (\d+)', text):
        tw_matches.append({
            'pos': m_tw.start(),
            'city': m_tw.group(1),
            'earliest_day': int(m_tw.group(2)),
            'latest_day': int(m_tw.group(3))
        })
        
    # Pattern 2: e.g., "From day {X} to day {Y}... in {City}"
    for m_tw in re.finditer(r'From day (\d+) to day (\d+)[^.]*? in ([A-Z][a-zA-Z]+)', text):
        tw_matches.append({
            'pos': m_tw.start(),
            'city': m_tw.group(3),
            'earliest_day': int(m_tw.group(1)),
            'latest_day': int(m_tw.group(2))
        })
        
    # Pattern 3: e.g., "During day {X} and day {Y}... in {City}"
    for m_tw in re.finditer(r'During day (\d+) and day (\d+)[^.]*? in ([A-Z][a-zA-Z]+)', text):
        tw_matches.append({
            'pos': m_tw.start(),
            'city': m_tw.group(3),
            'earliest_day': int(m_tw.group(1)),
            'latest_day': int(m_tw.group(2))
        })
        
    # Sort time windows by their appearance in the text
    tw_matches.sort(key=lambda x: x['pos'])
    time_windows = []
    for tw in tw_matches:
        time_windows.append({
            "city": tw["city"],
            "earliest_day": tw["earliest_day"],
            "latest_day": tw["latest_day"]
        })

    # Assemble and return the complete JSON string
    ans = {
        "total_days": total_days,
        "cities": cities,
        "flights": flights,
        "time_windows": time_windows
    }

    return json.dumps(ans)
