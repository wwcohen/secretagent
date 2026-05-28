"""No-arg evaluator for the NaturalPlan meeting-planning task.

Used by the generic runner, e.g.::

    uv run python -m secretagent.cli.expt run --config conf/meeting.yaml \
      --evaluator evaluator.MeetingEvaluator

Trace info (full rollouts) is captured by setting
``evaluate.record_details=true``; the base Evaluator writes it into
results.jsonl.

Eval logic adapted from natural-plan/evaluate_meeting.py
(Google DeepMind, Apache 2.0 License).
"""
import collections
import datetime

from secretagent.evaluate import Evaluator


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


class MeetingEvaluator(Evaluator):
    def compare_predictions(self, predicted_output, expected_output):
        pred = str(predicted_output) if predicted_output is not None else ''
        return dict(correct=eval_meeting_single(pred, expected_output))
