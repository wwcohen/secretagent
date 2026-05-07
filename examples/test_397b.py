"""Test with the 397B model for ptools to check <answer> tag compliance."""
import sys
sys.stdout.reconfigure(line_buffering=True)

from secretagent.core import interface, _INTERFACES
from secretagent import config
from secretagent.orchestrate import PtoolCatalog, compose_with_retry, build_pipeline
from secretagent.orchestrate.pipeline import _entry_signature_from_interface


@interface
def parse_numbers(problem: str) -> str:
    """Extract all numbers mentioned in the math problem.
    Return them as a comma-separated string of numbers.
    Example: "Alice has 5 apples and Bob has 3 oranges" -> "5, 3"
    """

@interface
def identify_operation(problem: str) -> str:
    """Determine what math operation the problem is asking for.
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
    """

@interface
def solve_math(problem: str) -> str:
    """Solve the math word problem step by step."""
    ...


BIG_MODEL = 'together_ai/Qwen/Qwen3.5-397B-A17B'
SMALL_MODEL = 'together_ai/Qwen/Qwen3.5-9B'

TEST_CASES = [
    {'problem': 'Alice has 12 apples and gives 4 to Bob. How many apples does Alice have now?', 'expected': '8'},
    {'problem': 'A store has 25 shirts. They sell 7 today. How many are left?', 'expected': '18'},
    {'problem': 'Tom read 15 pages yesterday and 23 today. How many total?', 'expected': '38'},
]


def run_with_model(model_name, label):
    print(f'\n{"=" * 60}')
    print(f'{label}: {model_name}')
    print(f'{"=" * 60}')

    config.configure(
        llm={'model': model_name},
        orchestrate={'model': BIG_MODEL},
        cachier={'enable_caching': False},
    )

    parse_numbers.implement_via('simulate')
    identify_operation.implement_via('simulate')
    compute_result.implement_via('simulate')
    format_answer.implement_via('simulate')

    # Hand-coded pipeline
    def pipeline(problem):
        nums = parse_numbers(problem)
        op = identify_operation(problem)
        result = compute_result(nums, op)
        answer = format_answer(problem, result)
        return answer

    for i, case in enumerate(TEST_CASES):
        print(f'\n--- Case {i+1}: {case["problem"][:50]}...')
        try:
            answer = pipeline(case['problem'])
            has_expected = case['expected'] in str(answer)
            print(f'  Answer: {answer}')
            print(f'  Contains "{case["expected"]}": {has_expected}')
        except Exception as e:
            print(f'  ERROR: {e}')


# Test with 397B
run_with_model(BIG_MODEL, 'BIG MODEL (397B)')

# Test with 9B
run_with_model(SMALL_MODEL, 'SMALL MODEL (9B)')

# Cleanup
for iface in [parse_numbers, identify_operation, compute_result, format_answer, solve_math]:
    if iface in _INTERFACES:
        _INTERFACES.remove(iface)

print('\nDone!')
