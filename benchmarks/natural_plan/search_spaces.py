"""Search space definitions for Natural Plan benchmark domains.

Methods are selected via dotlist overrides (not config files). Each method
maps to a list of dotlist strings that exactly mirror the Makefile targets.
The model dimension is a standard SearchDimension.

Pattern: outer loop over METHODS, inner search over models.
"""

from secretagent.optimize.encoder import SearchDimension

# -- Models --

MODELS = [
    "together_ai/deepseek-ai/DeepSeek-V3.1",
    "together_ai/openai/gpt-oss-20b",
    "together_ai/openai/gpt-oss-120b",
    "together_ai/Qwen/Qwen3.5-9B",
    "together_ai/google/gemma-3n-E4B-it",
    # NOTE: Qwen3.5-9B and gemma-3n-E4B-it do not support tool use.
    # react (simulate_pydantic) will fail with these models (scored 0%).
]

# -- Methods per domain --
# Each method maps to a list of dotlist overrides, copied exactly from the
# Makefile targets. The base config (--config-file conf/{task}.yaml) is
# handled by run_pareto.py, not here.

CALENDAR_METHODS = {
    "zs_struct": [
        "ptools.calendar_scheduling.method=simulate",
    ],
    "zs_unstruct": [
        "ptools.calendar_scheduling.method=prompt_llm",
        "ptools.calendar_scheduling.prompt_template_file=prompt_templates/zeroshot.txt",
    ],
    "workflow": [
        "ptools.calendar_scheduling.method=direct",
        "ptools.calendar_scheduling.fn=ptools_calendar.calendar_workflow",
    ],
    "pot": [
        "ptools.calendar_scheduling.method=program_of_thought",
        "ptools.calendar_scheduling.tools=[ptools_calendar.extract_constraints,ptools_calendar.solve_problem,ptools_calendar.format_answer]",
    ],
    "react": [
        "ptools.calendar_scheduling.method=simulate_pydantic",
        "ptools.calendar_scheduling.tools=[ptools_calendar.extract_constraints,ptools_calendar.solve_problem,ptools_calendar.format_answer]",
    ],
}

MEETING_METHODS = {
    "zs_struct": [
        "ptools.meeting_planning.method=simulate",
    ],
    "zs_unstruct": [
        "ptools.meeting_planning.method=prompt_llm",
        "ptools.meeting_planning.prompt_template_file=prompt_templates/zeroshot.txt",
    ],
    "workflow": [
        "ptools.meeting_planning.method=direct",
        "ptools.meeting_planning.fn=ptools_meeting.meeting_workflow",
    ],
    "pot": [
        "ptools.meeting_planning.method=program_of_thought",
        "ptools.meeting_planning.tools=[ptools_meeting.extract_constraints,ptools_meeting.solve_problem,ptools_meeting.format_answer]",
    ],
    "react": [
        "ptools.meeting_planning.method=simulate_pydantic",
        "ptools.meeting_planning.tools=[ptools_meeting.extract_constraints,ptools_meeting.solve_problem,ptools_meeting.format_answer]",
    ],
}

TRIP_METHODS = {
    "zs_struct": [
        "ptools.trip_planning.method=simulate",
    ],
    "zs_unstruct": [
        "ptools.trip_planning.method=prompt_llm",
        "ptools.trip_planning.prompt_template_file=prompt_templates/zeroshot.txt",
    ],
    "workflow": [
        "ptools.trip_planning.method=direct",
        "ptools.trip_planning.fn=ptools_trip.trip_workflow",
    ],
    "pot": [
        "ptools.trip_planning.method=program_of_thought",
        "ptools.trip_planning.tools=[ptools_trip.extract_constraints,ptools_trip.solve_problem,ptools_trip.format_answer]",
    ],
    "react": [
        "ptools.trip_planning.method=simulate_pydantic",
        "ptools.trip_planning.tools=[ptools_trip.extract_constraints,ptools_trip.solve_problem,ptools_trip.format_answer]",
    ],
}

# -- Config file per domain --

DOMAIN_CONFIGS = {
    "calendar": "conf/calendar.yaml",
    "meeting": "conf/meeting.yaml",
    "trip": "conf/trip.yaml",
}

# -- Search space builders --


def calendar_space() -> tuple[list[SearchDimension], list[str]]:
    """Model dimension only; methods are applied as dotlist overrides."""
    dims = [
        SearchDimension(key="llm.model", values=MODELS),
    ]
    return dims, []


def meeting_space() -> tuple[list[SearchDimension], list[str]]:
    dims = [
        SearchDimension(key="llm.model", values=MODELS),
    ]
    return dims, []


def trip_space() -> tuple[list[SearchDimension], list[str]]:
    dims = [
        SearchDimension(key="llm.model", values=MODELS),
    ]
    return dims, []


DOMAIN_SPACES = {
    "calendar": calendar_space,
    "meeting": meeting_space,
    "trip": trip_space,
}

DOMAIN_METHODS = {
    "calendar": CALENDAR_METHODS,
    "meeting": MEETING_METHODS,
    "trip": TRIP_METHODS,
}
