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
        - preference: "earliest" or "latest" or null
        - schedules: dict mapping participant name to dict mapping day to
          list of busy intervals e.g. {"Alice": {"Monday": [["9:00","10:00"]]}}

        Use 24-hour format. For participants with wide-open calendars, use empty lists.

    Example:
        >>> parse_schedules("You need to schedule a meeting for Alice and Bob for half an hour on Monday between 9:00 and 17:00. Alice is busy 9:00-10:00. Bob has no meetings.")
        '{"participants": ["Alice", "Bob"], "duration_minutes": 30, "working_hours": ["9:00", "17:00"], "days": ["Monday"], "preference": "earliest", "schedules": {"Alice": {"Monday": [["9:00", "10:00"]]}, "Bob": {"Monday": []}}}'
    """


@interface
def find_available_slots(problem_text: str, schedules_json: str) -> str:
    """Find valid meeting slots that work for all participants.

    Algorithm (be precise — interval arithmetic must be exact):
      1. For each requested day, build the list of FREE intervals for each
         participant (the complement of their busy intervals within
         working_hours). A participant with no busy intervals on that day
         has the single free interval [working_hours_start, working_hours_end].
      2. Compute the INTERSECTION of all participants' free intervals on
         that day (only times when EVERYONE is free).
      3. From each common-free interval, enumerate every slot of length
         duration_minutes that fits inside it. Slide in 30-min steps
         starting from the interval's start.

    Args:
        problem_text: The original problem text (same string you passed to
            parse_schedules).
        schedules_json: The JSON STRING output returned by parse_schedules.
            Pass the raw JSON string as-is — do NOT parse it into a dict first.

    Returns:
        A JSON string encoding a list of slot dicts, sorted by day order
        then start time:
        [{"day": str, "start": str, "end": str}, ...]
        Each slot must be EXACTLY duration_minutes long (end - start ==
        duration_minutes). Use 24-hour "HH:MM" format.

    Examples:
        # 30-minute meeting, 2 participants, 1 day:
        >>> find_available_slots(
        ...     "Schedule Alice and Bob for 30 min on Monday 9-17. Alice busy 9:00-10:00.",
        ...     '{"participants": ["Alice","Bob"], "duration_minutes": 30, "working_hours": ["9:00","17:00"], "days": ["Monday"], "schedules": {"Alice": {"Monday": [["9:00","10:00"]]}, "Bob": {"Monday": []}}}')
        '[{"day": "Monday", "start": "10:00", "end": "10:30"}, {"day": "Monday", "start": "10:30", "end": "11:00"}]'

        # 60-minute meeting, 3 participants, multiple busy intervals.
        # Alice free 9-10, 11-13, 14:30-17. Bob free 9-12, 13-15, 16-17.
        # Carol free 9:30-13:30, 14-17. Common-free 60-min slots on Monday:
        # 11:00-12:00 (all three free), 14:30-15:00 too short, no others fit 60 min.
        >>> find_available_slots(
        ...     "Schedule Alice, Bob and Carol for one hour on Monday 9-17.",
        ...     '{"participants": ["Alice","Bob","Carol"], "duration_minutes": 60, "working_hours": ["9:00","17:00"], "days": ["Monday"], "schedules": {"Alice": {"Monday": [["10:00","11:00"],["13:00","14:30"]]}, "Bob": {"Monday": [["12:00","13:00"],["15:00","16:00"]]}, "Carol": {"Monday": [["9:00","9:30"],["13:30","14:00"]]}}}')
        '[{"day": "Monday", "start": "11:00", "end": "12:00"}, {"day": "Monday", "start": "16:00", "end": "17:00"}]'
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
