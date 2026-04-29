"""Auto-generated code-distilled implementation for build_trip_plan."""

import json
import re

def build_trip_plan(prompt, constraints_str, route_str):
    try:
        constraints = json.loads(constraints_str) if constraints_str.strip().startswith('{') else None
        if constraints is None:
            return None
        
        route = json.loads(route_str) if route_str.strip().startswith('[') else None
        if route is None or len(route) == 0:
            # Try to extract route from constraints if route is empty or missing
            route_match = re.search(r'\[.*?\]', route_str)
            if route_match:
                route = json.loads(route_match.group())
            if not route:
                return None

        total_days = constraints.get("total_days", 0)
        cities = constraints.get("cities", {})
        num_cities = len(route)

        lines = []
        header = f"Here is the trip plan for visiting the {num_cities} European cities for {total_days} days:"
        lines.append(header)

        current_day = 1
        for i, city in enumerate(route):
            duration = cities.get(city, 1)
            
            if i == len(route) - 1:
                # Last city gets remaining days
                remaining = total_days - current_day + 1
                duration = remaining if remaining > 0 else duration
            
            end_day = current_day + duration - 1
            
            if i > 0:
                # Add flight line
                prev_city = route[i - 1]
                lines.append(f"**Day {current_day}:** Fly from {prev_city} to {city}.")
            
            if end_day >= current_day:
                if current_day == end_day:
                    lines.append(f"**Day {current_day}:** Visit {city} for {duration} day{'s' if duration != 1 else ''}.")
                else:
                    lines.append(f"**Day {current_day}-{end_day}:** Visit {city} for {duration} days.")
            else:
                lines.append(f"**Day {current_day}:** Visit {city} for {duration} days.")
            
            current_day = end_day

        return "\n".join(lines)
    except Exception:
        return None
