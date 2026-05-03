"""Auto-generated code-distilled implementation for parse_trip_constraints."""

import re
import json

def parse_trip_constraints(text):
    try:
        # Extract total days
        total_days_match = re.search(r'for (\d+) days in total', text)
        if not total_days_match:
            return None
        total_days = int(total_days_match.group(1))
        
        # Extract cities and their durations in order of appearance
        # Patterns: "stay in X for N days", "spend N days in X", "visit X for N days"
        city_days = {}
        city_order = []
        
        # Find all city-duration mentions in order
        patterns = [
            r'(?:stay in|visit)\s+([A-Z][a-zA-Zéè]+(?:\s+[A-Z][a-zA-Zéè]+)*)\s+for\s+(\d+)\s+days',
            r'spend\s+(\d+)\s+days\s+in\s+([A-Z][a-zA-Zéè]+(?:\s+[A-Z][a-zA-Zéè]+)*)',
        ]
        
        # Collect all matches with their positions
        matches_with_pos = []
        for line in text.split('\n'):
            for pat in patterns:
                for m in re.finditer(pat, line):
                    pos = text.index(line) + m.start()
                    if pat == patterns[1]:
                        city = m.group(2)
                        days = int(m.group(1))
                    else:
                        city = m.group(1)
                        days = int(m.group(2))
                    matches_with_pos.append((pos, city, days))
        
        matches_with_pos.sort(key=lambda x: x[0])
        for _, city, days in matches_with_pos:
            if city not in city_days:
                city_order.append(city)
                city_days[city] = days
        
        # Extract flights section
        flights_section_match = re.search(r'Here are the cities that have direct flights:\n(.+?)(?:\n\n|\n*Find)', text, re.DOTALL)
        if not flights_section_match:
            return None
        flights_text = flights_section_match.group(1).strip()
        
        flights = {}
        # Parse flight connections
        # Handle "from X to Y, Z and W" and "X and Y"
        segments = re.split(r',\s*', flights_text.rstrip('.'))
        
        for segment in segments:
            segment = segment.strip()
            from_match = re.match(r'from\s+(.+?)\s+to\s+(.+)', segment)
            if from_match:
                src = from_match.group(1).strip()
                dests = re.split(r'\s+and\s+|\s*,\s*', from_match.group(2).strip())
                dests = [d.strip().rstrip('.') for d in dests]
                for d in dests:
                    flights.setdefault(src, []).append(d)
                    flights.setdefault(d, []).append(src)
            else:
                cities_in_seg = re.split(r'\s+and\s+', segment)
                cities_in_seg = [c.strip().rstrip('.') for c in cities_in_seg]
                if len(cities_in_seg) == 2:
                    a, b = cities_in_seg
                    flights.setdefault(a, []).append(b)
                    flights.setdefault(b, []).append(a)
        
        # Remove duplicates while preserving order
        for key in flights:
            seen = set()
            unique = []
            for v in flights[key]:
                if v not in seen:
                    seen.add(v)
                    unique.append(v)
            flights[key] = unique
        
        # Extract time windows
        time_windows = []
        tw_patterns = [
            r'(?:attend a (?:workshop|conference|meeting)|there is a[n]? [\w\s]+you want to attend) in ([A-Z][a-zA-Zéè]+(?:\s+[A-Z][a-zA-Zéè]+)*) between day (\d+) and day (\d+)',
            r'[Ff]rom day (\d+) to day (\d+),.*?(?:attend|want to attend) in ([A-Z][a-zA-Zéè]+(?:\s+[A-Z][a-zA-Zéè]+)*)',
        ]
        
        for pat in tw_patterns:
            for m in re.finditer(pat, text):
                groups = m.groups()
                if len(groups) == 3:
                    if groups[0].isdigit():
                        city, earliest, latest = groups[2], int(groups[0]), int(groups[1])
                    else:
                        city, earliest, latest = groups[0], int(groups[1]), int(groups[2])
                    time_windows.append({"city": city, "earliest_day": earliest, "latest_day": latest})
        
        cities_ordered = {c: city_days[c] for c in city_order}
        
        result = {"total_days": total_days, "cities": cities_ordered, "flights": flights, "time_windows": time_windows}
        return json.dumps(result)
    except Exception:
        return None
