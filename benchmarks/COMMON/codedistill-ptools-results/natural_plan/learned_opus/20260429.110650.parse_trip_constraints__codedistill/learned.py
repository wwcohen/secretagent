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
        
        # Extract cities and their durations (in order of appearance)
        city_patterns = [
            r'(?:spend|stay in|visit)\s+(\d+)\s+days?\s+in\s+([A-Z][a-zA-Z]+)',
            r'(?:spend|stay in|visit)\s+([A-Z][a-zA-Z]+)\s+for\s+(\d+)\s+days?',
        ]
        
        cities = {}
        # Find all city mentions with days
        for match in re.finditer(r'(?:spend|stay in|visit)\s+(\d+)\s+days?\s+in\s+([A-Z][a-zA-Z]+)', text):
            days = int(match.group(1))
            city = match.group(2)
            cities[city] = days
        for match in re.finditer(r'(?:spend|stay in|visit)\s+([A-Z][a-zA-Z]+)\s+for\s+(\d+)\s+days?', text):
            city = match.group(1)
            days = int(match.group(2))
            cities[city] = days
        
        # Extract flights section
        flights_section_match = re.search(r'Here are the cities that have direct flights:\n(.+?)(?:\n\n|\nFind)', text, re.DOTALL)
        if not flights_section_match:
            return None
        flights_text = flights_section_match.group(1).strip()
        
        # Parse flight connections
        flights = {}
        for city in cities:
            flights[city] = []
        
        # Split by comma and period to get individual route descriptions
        route_parts = re.split(r'[,\.]\s*', flights_text)
        
        for part in route_parts:
            part = part.strip()
            if not part:
                continue
            # "X and Y" - bidirectional
            bi_match = re.match(r'([A-Z][a-zA-Z]+)\s+and\s+([A-Z][a-zA-Z]+)', part)
            # "from X to Y" - directional (but looking at examples, seems treated as bidirectional)
            dir_match = re.match(r'from\s+([A-Z][a-zA-Z]+)\s+to\s+([A-Z][a-zA-Z]+)', part)
            
            if dir_match:
                city_a = dir_match.group(1)
                city_b = dir_match.group(2)
                if city_a not in flights:
                    flights[city_a] = []
                if city_b not in flights:
                    flights[city_b] = []
                if city_b not in flights[city_a]:
                    flights[city_a].append(city_b)
                if city_a not in flights[city_b]:
                    flights[city_b].append(city_a)
            elif bi_match:
                city_a = bi_match.group(1)
                city_b = bi_match.group(2)
                if city_a not in flights:
                    flights[city_a] = []
                if city_b not in flights:
                    flights[city_b] = []
                if city_b not in flights[city_a]:
                    flights[city_a].append(city_b)
                if city_a not in flights[city_b]:
                    flights[city_b].append(city_a)
        
        # Extract time windows
        time_windows = []
        tw_patterns = [
            r'(?:During|From|between)\s+day\s+(\d+)\s+(?:and|to)\s+day\s+(\d+)[,\s]+.*?(?:in|at)\s+([A-Z][a-zA-Z]+)',
            r'(?:in|at)\s+([A-Z][a-zA-Z]+)\s+between\s+day\s+(\d+)\s+(?:and|to)\s+day\s+(\d+)',
        ]
        
        for match in re.finditer(r'(?:During|From)\s+day\s+(\d+)\s+(?:and|to)\s+day\s+(\d+),\s+.*?(?:in|at)\s+([A-Z][a-zA-Z]+)', text):
            time_windows.append({"city": match.group(3), "earliest_day": int(match.group(1)), "latest_day": int(match.group(2))})
        
        for match in re.finditer(r'(?:in|at)\s+([A-Z][a-zA-Z]+)\s+between\s+day\s+(\d+)\s+(?:and|to)\s+day\s+(\d+)', text):
            time_windows.append({"city": match.group(1), "earliest_day": int(match.group(2)), "latest_day": int(match.group(3))})
        
        result = {
            "total_days": total_days,
            "cities": cities,
            "flights": flights,
            "time_windows": time_windows
        }
        
        return json.dumps(result)
    
    except Exception:
        return None
