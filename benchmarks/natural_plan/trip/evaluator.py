"""No-arg evaluator for the NaturalPlan trip-planning task.

Used by the generic runner, e.g.::

    uv run python -m secretagent.cli.expt run --config conf/trip.yaml \
      --evaluator evaluator.TripEvaluator

Trace info (full rollouts) is captured by setting
``evaluate.record_details=true``; the base Evaluator writes it into
results.jsonl.

Eval logic adapted from natural-plan/evaluate_trip.py
(Google DeepMind, Apache 2.0 License).
"""
import re

from secretagent.evaluate import Evaluator


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


class TripEvaluator(Evaluator):
    def compare_predictions(self, predicted_output, expected_output):
        pred = str(predicted_output) if predicted_output is not None else ''
        return dict(correct=eval_trip_single(pred, expected_output))
