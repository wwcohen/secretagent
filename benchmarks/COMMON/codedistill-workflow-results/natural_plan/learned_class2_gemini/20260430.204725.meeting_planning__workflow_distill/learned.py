"""Auto-generated workflow-distilled implementation for meeting_planning.

Calls existing tools from ptools_meeting.
"""

from ptools_meeting import *

def meeting_planning(prompt: str) -> str:
    """Solve a meeting planning problem by orchestrating parsing, routing, and formatting tools."""
    try:
        # Step 1: Parse the problem constraints and meeting information
        parsed_info = parse_meeting_info(prompt)
        if not parsed_info:
            return None
            
        # Step 2: Determine the optimal visit order
        visit_order = plan_visit_order(prompt, parsed_info)
        if not visit_order:
            return None
            
        # Step 3: Build and format the final meeting plan
        plan = build_meeting_plan(prompt, parsed_info, visit_order)
        if not plan:
            return None
            
        return str(plan)
        
    except Exception:
        # Return None if any step fails to gracefully fall back
        return None
