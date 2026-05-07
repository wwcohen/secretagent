"""
Evaluation utilities for Natural Plan benchmark.

Core eval functions extracted from natural-plan/evaluate_*.py
(Google DeepMind, Apache 2.0 License).
"""

import collections
import datetime
import re
from typing import Any, List, Optional, Tuple


# ============================================================================
# Calendar Scheduling Evaluation
# ============================================================================

def calendar_hour_to_num(hr_str: str) -> float:
    """Convert 'HH:MM' to numeric hours (e.g., '14:30' -> 14.5)."""
    parts = hr_str.split(':')
    return float(parts[0]) + (0.5 if parts[1] == '30' else 0.0)


def calendar_parse_response(response: str) -> Tuple[str, float, float]:
    """Parse calendar scheduling response.

    Returns (day, start_hour, end_hour).
    Expected format: 'Monday, 14:30 - 15:30'
    """
    time_strs = re.findall(r'[A-Za-z]+, [0-9]+:[0-9]+ - [0-9]+:[0-9]+', response)
    if not time_strs:
        return '', -1, -1
    time_str = time_strs[0]
    day, hour_str = time_str.split(',')[0].strip(), time_str.split(',')[1].strip()
    start_hour, end_hour = hour_str.split('-')[0].strip(), hour_str.split('-')[1].strip()
    return day, calendar_hour_to_num(start_hour), calendar_hour_to_num(end_hour)


def eval_calendar_single(response: str, golden: str) -> bool:
    """Evaluate a single calendar scheduling instance. Returns True if correct."""
    r_day, r_start, r_end = calendar_parse_response(response)
    s_day, s_start, s_end = calendar_parse_response(golden)
    return r_day == s_day and r_start == s_start and r_end == s_end


def eval_calendar_batch(responses: List[str], goldens: List[str]) -> float:
    """Compute solve rate for a batch of calendar scheduling instances."""
    solved = sum(1 for r, g in zip(responses, goldens) if eval_calendar_single(r, g))
    return float(solved) / len(responses) if responses else 0.0


# ============================================================================
# Meeting Planning Evaluation
# ============================================================================

def _meeting_convert_time(time_str: str) -> datetime.datetime:
    """Convert '10:30AM' to datetime object."""
    return datetime.datetime.strptime(time_str, "%I:%M%p")


def meeting_process_constraints(data: list) -> dict:
    """Process meeting constraints into structured dict."""
    constraints = collections.defaultdict(dict)
    for name, location, times, meeting_time in data:
        constraints[name]["location"] = location
        start_time = _meeting_convert_time(times.split("to")[0].strip())
        end_time = _meeting_convert_time(times.split("to")[1].strip())
        constraints[name]["start_time"] = start_time
        constraints[name]["end_time"] = end_time
        constraints[name]["meeting_time"] = meeting_time
    return constraints


def meeting_parse_text_plan(plan: str) -> list:
    """Parse text plan into list of steps."""
    prefix = "SOLUTION:"
    if prefix in plan:
        plan = plan[plan.find(prefix) + len(prefix):].strip()
    plan = plan.split(".")
    return [step.strip() for step in plan if step.strip()]


def meeting_validator_from_text(
    plan: list,
    processed_constraints: dict,
    start_location: str,
    initial_time: str,
    dist_matrix: dict,
) -> int:
    """Compute number of valid meetings in a text-format plan."""
    met_with = {}
    score = 0
    cur_location = start_location
    cur_time = _meeting_convert_time(initial_time)

    for step in plan:
        try:
            if step.startswith("You start"):
                continue
            elif step.startswith("You travel"):
                destination = step.split("travel to ")[1].split(" in")[0].strip()
                cur_time = cur_time + datetime.timedelta(
                    minutes=dist_matrix[cur_location][destination]
                )
                cur_location = destination
            elif step.startswith("You wait"):
                raw_end_time = step.split("wait until ")[1].split(".")[0].strip()
                end_time = _meeting_convert_time(raw_end_time)
                if end_time <= cur_time:
                    raise ValueError("Cannot go backwards in time")
                cur_time = end_time
            elif step.startswith("You meet"):
                person = step.split("meet ")[1].split(" for")[0].strip()
                if person in met_with:
                    raise ValueError(f"Already met {person}")
                met_with[person] = 1
                new_time = cur_time + datetime.timedelta(
                    minutes=processed_constraints[person]["meeting_time"]
                )
                if (
                    cur_location == processed_constraints[person]["location"]
                    and cur_time >= processed_constraints[person]["start_time"]
                    and new_time <= processed_constraints[person]["end_time"]
                ):
                    score += 1
                    cur_time = new_time
                else:
                    raise ValueError("Invalid meeting time or location")
            else:
                raise ValueError("Unknown plan format")
        except (ValueError, KeyError):
            break

    return score


def eval_meeting_single(response: str, instance: dict) -> bool:
    """Evaluate a single meeting planning instance.

    Returns True if the response achieves the same number of valid meetings
    as the golden plan.
    """
    start_location, initial_time = instance["constraints"][0]
    constraints = meeting_process_constraints(instance["constraints"][1:])
    dist_matrix = instance["dist_matrix"]

    # Score the prediction
    pred_plan = meeting_parse_text_plan(response)
    pred_score = meeting_validator_from_text(
        pred_plan, constraints, start_location, initial_time, dist_matrix
    )

    # Score the golden plan
    golden_plan = instance["golden_plan"]
    if isinstance(golden_plan, str):
        golden_plan = meeting_parse_text_plan(golden_plan)
    golden_score = meeting_validator_from_text(
        golden_plan, constraints, start_location, initial_time, dist_matrix
    )

    return pred_score == golden_score


# ============================================================================
# Trip Planning Evaluation
# ============================================================================

def trip_parse_response(response: str) -> list:
    """Parse trip planning response into list of (city, stay_days) tuples."""
    pattern_visit = r'\d+-\d+'
    pattern_flight = r'.*Day (\d+).*from (\w+) to (\w+)'
    pattern_days = r'European cities for (\d+) days'

    days, flights, flight_days = [], [], []
    total_days = None
    for piece in response.split('\n'):
        days_match = re.findall(pattern_days, piece)
        if days_match:
            total_days = int(days_match[0])
        visit_match = re.findall(pattern_visit, piece)
        if visit_match:
            days.append(visit_match[0])
            end_day = int(visit_match[0].split('-')[1])
            if end_day == total_days:
                break
        flight_match = re.findall(pattern_flight, piece)
        if flight_match:
            flights.append(flight_match[0])

    visit_cities, parsed_plan = [], []
    for flight_day, begin_city, end_city in flights:
        flight_days.append(int(flight_day))
        if not visit_cities:
            visit_cities.append(begin_city)
            visit_cities.append(end_city)
        else:
            visit_cities.append(end_city)

    if not days or not flights or not visit_cities:
        return []
    last_day = int(days[-1].split('-')[1])
    flight_days = [1] + flight_days + [last_day]
    for i, visit_city in enumerate(visit_cities):
        city_stay = flight_days[i + 1] - flight_days[i] + 1
        parsed_plan.append((visit_city, city_stay))

    return parsed_plan


def eval_trip_single(response: str, instance: dict) -> bool:
    """Evaluate a single trip planning instance. Returns True if exact match."""
    cities = instance["cities"]
    durations = instance["durations"]

    parsed_plan = trip_parse_response(response)
    stays = [x for x in cities.split('**') if x]
    days = [int(x) for x in durations.split('**') if x]
    num_stays = min(len(stays), len(parsed_plan))
    num_match = 0
    for i in range(num_stays):
        if stays[i] == parsed_plan[i][0] and days[i] == parsed_plan[i][1]:
            num_match += 1
        else:
            break
    return num_match == len(stays) and num_match > 0
