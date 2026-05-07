"""Orchestrator comparison: hand-coded vs auto-composed pipelines.

Tests the orchestrator on a custom reasoning task where the 9B model
can follow instructions. Compares accuracy between hand-coded and
auto-composed pipelines.

Usage:
    source .env && uv run python examples/orchestrate_comparison.py
"""

import json
import sys
import time

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
from secretagent.core import interface, _INTERFACES
from secretagent import config
from secretagent.orchestrate import (
    PtoolCatalog, compose_with_retry, build_pipeline,
)
from secretagent.orchestrate.pipeline import _entry_signature_from_interface


# ── Define ptools for a math reasoning task ───────────────────────────

@interface
def parse_numbers(problem: str) -> str:
    """Extract all numbers mentioned in the math problem.

    Given a word problem, identify and list all numerical values mentioned.
    Return them as a comma-separated string of numbers.

    Example: "Alice has 5 apples and Bob has 3 oranges" -> "5, 3"
    """

@interface
def identify_operation(problem: str) -> str:
    """Determine what math operation the problem is asking for.

    Read the problem and determine if it needs addition, subtraction,
    multiplication, or division.

    Return one of: "addition", "subtraction", "multiplication", "division"
    """

@interface
def compute_result(numbers: str, operation: str) -> str:
    """Compute the result of applying the operation to the numbers.

    Given a comma-separated string of numbers and an operation name,
    compute and return the numerical result as a string.

    Example: numbers="5, 3", operation="addition" -> "8"
    """

@interface
def format_answer(problem: str, result: str) -> str:
    """Format the final answer as a complete sentence.

    Given the original problem and the computed result, write a
    one-sentence answer.

    Example: problem="How many apples total?", result="8" ->
        "The total number of apples is 8."
    """

@interface
def solve_math_problem(problem: str) -> str:
    """Solve the math word problem step by step."""
    ...


# ── Test dataset ──────────────────────────────────────────────────────

TEST_CASES = [
    {
        'problem': 'Alice has 12 apples and gives 4 to Bob. How many apples does Alice have now?',
        'expected_number': '8',
    },
    {
        'problem': 'A store has 25 shirts. They sell 7 shirts today. How many shirts are left?',
        'expected_number': '18',
    },
    {
        'problem': 'Tom read 15 pages yesterday and 23 pages today. How many pages did he read in total?',
        'expected_number': '38',
    },
    {
        'problem': 'A classroom has 6 rows with 5 desks in each row. How many desks are there?',
        'expected_number': '30',
    },
    {
        'problem': 'Maria had 20 candies and ate 3. How many candies does she have left?',
        'expected_number': '17',
    },
    {
        'problem': 'A baker made 48 cookies and packed them into boxes of 8. How many boxes did he fill?',
        'expected_number': '6',
    },
    {
        'problem': 'John has 9 marbles and his friend gives him 14 more. How many marbles does John have?',
        'expected_number': '23',
    },
    {
        'problem': 'A garden has 3 rows of 7 flowers each. How many flowers are in the garden?',
        'expected_number': '21',
    },
    {
        'problem': 'Sarah had 50 stickers and gave 12 to her sister. How many stickers does Sarah have now?',
        'expected_number': '38',
    },
    {
        'problem': 'A library receives 35 new books and already has 120 books. How many books does the library have now?',
        'expected_number': '155',
    },
]


def check_answer(answer: str, expected_number: str) -> bool:
    """Check if the answer contains the expected number."""
    return expected_number in answer


def run_experiment(name: str, pipeline_fn, test_cases: list) -> dict:
    """Run a pipeline on test cases and collect metrics."""
    results = []
    total_time = 0

    for i, case in enumerate(test_cases):
        start = time.time()
        try:
            answer = pipeline_fn(case['problem'])
            elapsed = time.time() - start
            correct = check_answer(str(answer), case['expected_number'])
            results.append({
                'case': i,
                'problem': case['problem'][:60] + '...',
                'expected': case['expected_number'],
                'answer': str(answer)[:100],
                'correct': correct,
                'time': elapsed,
                'error': None,
            })
        except Exception as e:
            elapsed = time.time() - start
            results.append({
                'case': i,
                'problem': case['problem'][:60] + '...',
                'expected': case['expected_number'],
                'answer': None,
                'correct': False,
                'time': elapsed,
                'error': str(e)[:100],
            })
        total_time += elapsed

    accuracy = sum(1 for r in results if r['correct']) / len(results)
    errors = sum(1 for r in results if r['error'])

    return {
        'name': name,
        'accuracy': accuracy,
        'errors': errors,
        'total': len(results),
        'total_time': total_time,
        'results': results,
    }


def main():
    # Configure
    config.configure(
        llm={'model': 'together_ai/Qwen/Qwen3.5-9B'},
        orchestrate={
            'model': 'together_ai/Qwen/Qwen3.5-9B',
            'max_retries': 3,
        },
        echo={'orchestrate': True},
        cachier={'enable_caching': False},
    )

    # Implement ptools
    parse_numbers.implement_via('simulate')
    identify_operation.implement_via('simulate')
    compute_result.implement_via('simulate')
    format_answer.implement_via('simulate')

    # ── Experiment 1: Hand-coded pipeline ─────────────────────────────

    print('=' * 70)
    print('EXPERIMENT 1: Hand-coded pipeline')
    print('=' * 70)

    def hand_coded_pipeline(problem: str) -> str:
        numbers = parse_numbers(problem)
        operation = identify_operation(problem)
        result = compute_result(numbers, operation)
        answer = format_answer(problem, result)
        return answer

    baseline = run_experiment('hand_coded', hand_coded_pipeline, TEST_CASES)

    # ── Experiment 2: Orchestrated pipeline ───────────────────────────

    print('\n' + '=' * 70)
    print('EXPERIMENT 2: Orchestrated pipeline')
    print('=' * 70)

    catalog = PtoolCatalog.from_interfaces(
        [parse_numbers, identify_operation, compute_result, format_answer]
    )
    entry_sig = _entry_signature_from_interface(solve_math_problem)
    tool_interfaces = [parse_numbers, identify_operation, compute_result, format_answer]

    # Use first test case as smoke test
    def test_fn(code: str):
        pipeline = build_pipeline(code, solve_math_problem, tool_interfaces)
        result = pipeline(TEST_CASES[0]['problem'])
        assert isinstance(result, str) and len(result) > 0

    code, attempt = compose_with_retry(
        task_description=(
            'Solve a math word problem. Parse the numbers from the problem, '
            'identify the operation needed, compute the result, then format '
            'a complete sentence answer.'
        ),
        catalog=catalog,
        entry_signature=entry_sig,
        test_fn=test_fn,
    )

    print(f'\nPipeline generated on attempt {attempt}')

    orchestrated_pipeline = build_pipeline(code, solve_math_problem, tool_interfaces)
    print(f'Generated code:\n{orchestrated_pipeline.source}\n')

    orchestrated = run_experiment('orchestrated', orchestrated_pipeline, TEST_CASES)

    # ── Results comparison ────────────────────────────────────────────

    print('\n' + '=' * 70)
    print('RESULTS COMPARISON')
    print('=' * 70)

    print(f'\n{"Metric":<25} {"Hand-coded":<15} {"Orchestrated":<15}')
    print('-' * 55)
    print(f'{"Accuracy":<25} {baseline["accuracy"]:.0%}{"":<11} {orchestrated["accuracy"]:.0%}')
    print(f'{"Errors":<25} {baseline["errors"]}/{baseline["total"]}{"":<8} {orchestrated["errors"]}/{orchestrated["total"]}')
    print(f'{"Total time (s)":<25} {baseline["total_time"]:.1f}{"":<11} {orchestrated["total_time"]:.1f}')
    print(f'{"Pass@k (orchestrator)":<25} {"N/A":<15} {attempt}')

    print('\nPer-case results:')
    print(f'{"#":<4} {"Problem":<45} {"Exp":<5} {"HC":<5} {"Orch":<5}')
    print('-' * 64)
    for i in range(len(TEST_CASES)):
        b = baseline['results'][i]
        o = orchestrated['results'][i]
        hc_mark = 'Y' if b['correct'] else ('E' if b['error'] else 'N')
        or_mark = 'Y' if o['correct'] else ('E' if o['error'] else 'N')
        print(f'{i:<4} {b["problem"]:<45} {b["expected"]:<5} {hc_mark:<5} {or_mark:<5}')

    # Save results
    output = {
        'baseline': {k: v for k, v in baseline.items() if k != 'results'},
        'orchestrated': {k: v for k, v in orchestrated.items() if k != 'results'},
        'orchestrator_attempt': attempt,
        'generated_code': orchestrated_pipeline.source,
        'detailed_results': {
            'baseline': baseline['results'],
            'orchestrated': orchestrated['results'],
        },
    }
    with open('orchestrate_comparison_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f'\nDetailed results saved to orchestrate_comparison_results.json')


# ── Cleanup ───────────────────────────────────────────────────────────

def cleanup():
    for iface in [parse_numbers, identify_operation, compute_result,
                  format_answer, solve_math_problem]:
        if iface in _INTERFACES:
            _INTERFACES.remove(iface)


if __name__ == '__main__':
    try:
        main()
    finally:
        cleanup()
