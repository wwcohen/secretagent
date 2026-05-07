"""Quick end-to-end test with direct-implemented ptools."""
import sys
sys.stdout.reconfigure(line_buffering=True)

from secretagent.core import interface, _INTERFACES
from secretagent import config
from secretagent.orchestrate import PtoolCatalog, compose_with_retry, build_pipeline
from secretagent.orchestrate.pipeline import _entry_signature_from_interface


@interface
def parse_nums(problem: str) -> str:
    """Extract all numbers from the math problem as a comma-separated string.
    Example: "Alice has 5 apples and Bob has 3" -> "5, 3"
    """
    return '5, 3'

@interface
def identify_op(problem: str) -> str:
    """Determine the math operation: addition, subtraction, multiplication, or division."""
    return 'subtraction'

@interface
def compute(numbers: str, operation: str) -> str:
    """Apply the operation to the numbers and return the result as a string.
    Example: numbers="5, 3", operation="subtraction" -> "2"
    """
    return '2'

@interface
def solve(problem: str) -> str:
    """Solve the math word problem."""
    ...


# Implement
parse_nums.implement_via('direct')
identify_op.implement_via('direct')
compute.implement_via('direct')

config.configure(
    orchestrate={'model': 'together_ai/Qwen/Qwen3.5-397B-A17B'},
    cachier={'enable_caching': False},
)

# Test 1: Hand-coded
print('=== Hand-coded pipeline ===')


def hand_coded(problem):
    nums = parse_nums(problem)
    op = identify_op(problem)
    return compute(nums, op)


result = hand_coded('Alice has 5 apples and gives 3 to Bob.')
print(f'Hand-coded result: {result}')

# Test 2: Orchestrated
print()
print('=== Orchestrated pipeline ===')
catalog = PtoolCatalog.from_interfaces([parse_nums, identify_op, compute])
entry_sig = _entry_signature_from_interface(solve)
tools = [parse_nums, identify_op, compute]


def test_fn(code):
    p = build_pipeline(code, solve, tools)
    r = p('test problem')
    assert r is not None


code, attempt = compose_with_retry(
    'Parse the numbers from the problem, identify the operation, compute the result.',
    catalog, entry_sig, test_fn=test_fn, max_retries=3,
)

pipeline = build_pipeline(code, solve, tools)
print(f'Generated on attempt {attempt}')
print(f'Source:\n{pipeline.source}')
print()

result_orch = pipeline('Alice has 5 apples and gives 3 to Bob.')
print(f'Orchestrated result: {result_orch}')
print(f'Match: {result == result_orch}')

# Cleanup
for i in [parse_nums, identify_op, compute, solve]:
    _INTERFACES.remove(i)

print('\nDone!')
