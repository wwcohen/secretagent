"""Auto-generated workflow-distilled implementation for trip_planning.

Calls existing tools from ptools_trip.
"""

from ptools_trip import *

def trip_planning(prompt: str) -> str:
    """Solve a trip planning problem by parsing constraints, finding a valid route, and building the plan."""
    
    # Step 1: Parse the trip constraints from the prompt
    constraints_json = parse_trip_constraints(prompt)
    
    # Step 2: Find a valid route that satisfies all constraints
    route_json = find_valid_route(prompt, constraints_json)
    
    # Step 3: Build the formatted trip plan
    result = build_trip_plan(prompt, constraints_json, route_json)
    
    return result
