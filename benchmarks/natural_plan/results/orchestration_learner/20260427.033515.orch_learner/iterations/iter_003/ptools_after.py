"""Task-specific interfaces for NaturalPlan calendar scheduling.

Decomposition derived from LLM reasoning traces:
1. parse_schedules — extract participants, busy slots, duration, preference
2. find_available_slots — compute free slot intersections
3. select_and_format — pick best slot, format answer
"""

from secretagent.core import interface


@interface
def parse_schedules(problem_text: str) -> str:
    """Parse a calendar scheduling problem into structured JSON.

    Args:
        problem_text: The ENTIRE scheduling problem description as a single
            string. Pass the whole problem text (participants, their busy
            times, duration, preferences, working hours, etc.) as one
            argument — do NOT split it into multiple arguments.

    Returns:
        A JSON string encoding a dict with these keys:
        - participants: list of participant names
        - duration_minutes: meeting duration (30 or 60)
        - working_hours: [start_str, end_str] e.g. ["9:00", "17:00"]
        - days: list of day names e.g. ["Monday", "Tuesday"]
        - preference: "earliest" or "latest" or null (if no explicit preference)
        - schedules: dict mapping participant name to dict mapping day to
          list of busy intervals e.g. {"Alice": {"Monday": [["9:00","10:00"]]}}

        CRITICAL - NEGATIVE CONSTRAINTS:
        You MUST encode any negative scheduling constraints (e.g., "avoid more meetings on", "rather not meet on", "do not want to meet on", "can not meet on") as BUSY INTERVALS in the `schedules` dictionary.
        - If a participant avoids a whole day (e.g., "avoid Tuesday"), add ["00:00", "23:59"] to their schedule for that day.
        - If a participant avoids a day after a certain time (e.g., "Monday after 14:30"), add ["14:30", "23:59"] to their Monday schedule.
        - If a participant avoids a day before a certain time (e.g., "Wednesday before 12:00"), add ["00:00", "12:00"] to their Wednesday schedule.
        Do NOT drop these constraints; they MUST be added to their respective busy lists.

        Use 24-hour format. For participants with wide-open calendars, use empty lists unless they have a negative constraint.

    Example:
        >>> parse_schedules("You need to schedule a meeting for Alice and Bob for half an hour on Monday and Tuesday between 9:00 and 17:00. Alice is busy Mon 9:00-10:00. Bob has no meetings but would rather not meet on Tuesday. Alice cannot meet on Monday after 15:00.")
        '{"participants": ["Alice", "Bob"], "duration_minutes": 30, "working_hours": ["9:00", "17:00"], "days": ["Monday", "Tuesday"], "preference": null, "schedules": {"Alice": {"Monday": [["9:00", "10:00"], ["15:00", "23:59"]], "Tuesday": []}, "Bob": {"Monday": [], "Tuesday": [["00:00", "23:59"]]}}}'
    """


@interface
def find_available_slots(problem_text: str, schedules_json: str) -> str:
    """Find valid meeting slots that work for all participants.

    Args:
        problem_text: The original problem text (same string you passed to
            parse_schedules).
        schedules_json: The JSON STRING output returned by parse_schedules.
            Pass the raw JSON string as-is — do NOT parse it into a dict first.

    Returns:
        A JSON string encoding a list of slot dicts, sorted by day order
        then start time:
        [{"day": str, "start": str, "end": str}, ...]
        Each slot is at least duration_minutes long. Use 24-hour "HH:MM" format.

        CRITICAL: A valid slot MUST NOT overlap with ANY participant's busy intervals.
        Carefully check the `schedules_json` for every participant. If a slot falls inside a busy interval for ANY participant, DO NOT include it.

    Example:
        >>> find_available_slots(
        ...     "Schedule Alice and Bob for 30 min on Monday 9-17. Alice busy 9:00-10:00.",
        ...     '{"participants": ["Alice","Bob"], "duration_minutes": 30, "working_hours": ["9:00","17:00"], "days": ["Monday"], "schedules": {"Alice": {"Monday": [["9:00","10:00"]]}, "Bob": {"Monday": []}}}')
        '[{"day": "Monday", "start": "10:00", "end": "10:30"}, {"day": "Monday", "start": "10:30", "end": "11:00"}]'
    """


@interface
def select_and_format(slots_json: str, preference: str) -> str:
    """Pick the best slot based on preference and format the final answer.

    Args:
        slots_json: The JSON STRING output returned by find_available_slots
            (a JSON array of slot dicts). Pass the raw JSON string as-is.
        preference: Either "earliest" (pick the first slot) or "latest"
            (pick the last slot).

    Returns:
        A string with exactly this format:
        'Here is the proposed time: {Day}, {HH:MM} - {HH:MM}'

    Example:
        >>> select_and_format('[{"day": "Monday", "start": "10:00", "end": "10:30"}, {"day": "Monday", "start": "13:00", "end": "13:30"}]', "earliest")
        'Here is the proposed time: Monday, 10:00 - 10:30'
    """


@interface
def calendar_scheduling(prompt: str) -> str:
    """Solve a calendar scheduling problem.

    Given a scheduling problem describing participants, their busy times,
    meeting duration, and any preferences, return a single proposed meeting
    time that satisfies all constraints.

    Args:
        prompt: The full scheduling problem as one string.

    Returns:
        A string with exactly this format:
        'Here is the proposed time: {Day}, {HH:MM} - {HH:MM}'
    """
    ...


def calendar_workflow(prompt: str) -> str:
    schedules = parse_schedules(prompt)
    slots = find_available_slots(prompt, schedules)
    return select_and_format(slots, "earliest")

# --- Auto-generated by orchestration_learner --seed-orchestrate ---
def calendar_scheduling_orchestrated_seed(prompt: str) -> str:
    schedules_json = parse_schedules(prompt)
    slots_json = find_available_slots(prompt, schedules_json)

    # Extract the preference from the JSON string without importing the json module
    compact_json = schedules_json.replace(" ", "")
    if '"preference":"latest"' in compact_json:
        preference = "latest"
    else:
        preference = "earliest"

    return select_and_format(slots_json, preference)