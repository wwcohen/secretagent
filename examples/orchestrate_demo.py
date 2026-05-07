"""Orchestrator demo: auto-generate a pipeline from toy ptools.

Usage:
    source .env && uv run python examples/orchestrate_demo.py
"""

from secretagent.core import interface, _INTERFACES
from secretagent import config
from secretagent.orchestrate import (
    PtoolCatalog, compose, compose_with_retry, build_pipeline,
)
from secretagent.orchestrate.pipeline import _entry_signature_from_interface


# ── Define toy ptools ─────────────────────────────────────────────────

@interface
def double(x: int) -> int:
    """Double the input value. Returns x * 2."""
    return x * 2

@interface
def add_one(x: int) -> int:
    """Add one to the input. Returns x + 1."""
    return x + 1

@interface
def negate(x: int) -> int:
    """Negate the input. Returns -x."""
    return -x

@interface
def workflow(x: int) -> int:
    """Process x through a multi-step pipeline."""
    ...


# ── Implement tools ───────────────────────────────────────────────────

double.implement_via('direct')
add_one.implement_via('direct')
negate.implement_via('direct')

# ── Configure ─────────────────────────────────────────────────────────

config.configure(
    orchestrate={
        'model': 'together_ai/Qwen/Qwen3.5-397B-A17B',
        'max_retries': 3,
    },
    echo={'orchestrate': True},
    cachier={'enable_caching': False},
)


# ── Demo 1: Simple two-step pipeline ─────────────────────────────────

print('=' * 60)
print('Demo 1: Double then add one')
print('=' * 60)

catalog = PtoolCatalog.from_interfaces([double, add_one])
entry_sig = _entry_signature_from_interface(workflow)

tool_interfaces = [double, add_one]

def test_fn(code: str):
    pipeline = build_pipeline(code, workflow, tool_interfaces)
    result = pipeline(5)
    assert result == 11, f'Expected 11, got {result}'

code, attempt = compose_with_retry(
    task_description='Double the input x, then add one to the result.',
    catalog=catalog,
    entry_signature=entry_sig,
    test_fn=test_fn,
)

pipeline = build_pipeline(code, workflow, tool_interfaces)
print(f'\nGenerated on attempt {attempt}:')
print(pipeline.source)
print(f'\nworkflow(5) = {pipeline(5)}')
print(f'workflow(0) = {pipeline(0)}')
print(f'workflow(-3) = {pipeline(-3)}')


# ── Demo 2: Three-step pipeline ──────────────────────────────────────

print('\n' + '=' * 60)
print('Demo 2: Double, add one, then negate')
print('=' * 60)

catalog2 = PtoolCatalog.from_interfaces([double, add_one, negate])
tool_interfaces2 = [double, add_one, negate]

def test_fn2(code: str):
    pipeline = build_pipeline(code, workflow, tool_interfaces2)
    result = pipeline(5)
    assert result == -11, f'Expected -11, got {result}'

code2, attempt2 = compose_with_retry(
    task_description='Double x, then add one, then negate the result.',
    catalog=catalog2,
    entry_signature=entry_sig,
    test_fn=test_fn2,
)

pipeline2 = build_pipeline(code2, workflow, tool_interfaces2)
print(f'\nGenerated on attempt {attempt2}:')
print(pipeline2.source)
print(f'\nworkflow(5) = {pipeline2(5)}')  # double(5)=10, add_one(10)=11, negate(11)=-11
print(f'workflow(0) = {pipeline2(0)}')    # double(0)=0, add_one(0)=1, negate(1)=-1


# ── Cleanup ───────────────────────────────────────────────────────────

for iface in [double, add_one, negate, workflow]:
    if iface in _INTERFACES:
        _INTERFACES.remove(iface)

print('\nDone!')
