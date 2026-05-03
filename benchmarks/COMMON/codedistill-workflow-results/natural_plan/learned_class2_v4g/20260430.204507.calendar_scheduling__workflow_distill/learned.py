"""Auto-generated workflow-distilled implementation for calendar_scheduling.

Calls existing tools from ptools_calendar.
"""

from ptools_calendar import *

def calendar_scheduling(prompt: str) -> str:
    """
    Solves the calendar scheduling task end-to-end by orchestrating the provided tools.
    Returns None if any step fails or output is invalid, triggering a fallback.
    """
    try:
        # Step 1: Parse constraints and schedules into a structured format
        schedules_json = parse_schedules(prompt)
        if not schedules_json:
            return None
            
        # Step 2: Find available time slots honoring the constraints
        slots_json = find_available_slots(prompt, schedules_json)
        if not slots_json:
            return None
            
        # Step 3: Select an appropriate slot and format the final string output
        final_answer = select_and_format(prompt, schedules_json, slots_json)
        if not final_answer or not isinstance(final_answer, str):
            return None
            
        return final_answer

    except Exception:
        # Return None on any unexpected errors (e.g., parsing failures, tool exceptions)
        return None
