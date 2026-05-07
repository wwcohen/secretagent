"""Integration tests for the orchestrate package.

These tests call real LLM APIs via Together AI and require TOGETHER_API_KEY.
They validate the full compose → build → execute pipeline.
"""

import os
import pytest
from secretagent import config
from secretagent.core import interface, _INTERFACES
from secretagent.orchestrate import (
    PtoolCatalog, compose, compose_with_retry, build_pipeline,
)
from secretagent.orchestrate.pipeline import _entry_signature_from_interface

needs_together_key = pytest.mark.skipif(
    not os.environ.get('TOGETHER_API_KEY'),
    reason='TOGETHER_API_KEY not set',
)

ORCHESTRATOR_MODEL = 'together_ai/Qwen/Qwen3.5-397B-A17B'


# ── Toy ptools for testing ────────────────────────────────────────────

@interface
def orch_double(x: int) -> int:
    """Double the input value. Returns x * 2."""
    return x * 2

@interface
def orch_add_one(x: int) -> int:
    """Add one to the input. Returns x + 1."""
    return x + 1

@interface
def orch_negate(x: int) -> int:
    """Negate the input. Returns -x."""
    return -x

@interface
def orch_workflow(x: int) -> int:
    """Double x, then add one to the result."""
    ...


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Implement toy tools and configure for testing."""
    orch_double.implement_via('direct')
    orch_add_one.implement_via('direct')
    orch_negate.implement_via('direct')
    orch_workflow.implementation = None

    with config.configuration(
            orchestrate={'model': ORCHESTRATOR_MODEL} ):
        yield

    orch_double.implementation = None
    orch_add_one.implementation = None
    orch_negate.implementation = None
    orch_workflow.implementation = None


@needs_together_key
def test_compose_generates_valid_code():
    """compose() generates Python code that parses and uses the right tools."""
    catalog = PtoolCatalog.from_interfaces(
        [orch_double, orch_add_one], exclude=[]
    )
    entry_sig = _entry_signature_from_interface(orch_workflow)

    code = compose(
        task_description='Double the input x, then add one to the result.',
        catalog=catalog,
        entry_signature=entry_sig,
        model=ORCHESTRATOR_MODEL,
    )

    assert 'double' in code or 'orch_double' in code
    assert len(code.strip()) > 0


@needs_together_key
def test_compose_and_execute():
    """Full pipeline: compose code, build pipeline, execute correctly."""
    catalog = PtoolCatalog.from_interfaces(
        [orch_double, orch_add_one],
    )
    entry_sig = _entry_signature_from_interface(orch_workflow)

    code = compose(
        task_description='Double the input x, then add one to the result.',
        catalog=catalog,
        entry_signature=entry_sig,
        model=ORCHESTRATOR_MODEL,
    )

    pipeline = build_pipeline(code, orch_workflow, [orch_double, orch_add_one])
    result = pipeline(5)
    assert result == 11, f'Expected 11, got {result}'

    # Test with another input
    result2 = pipeline(0)
    assert result2 == 1, f'Expected 1, got {result2}'


@needs_together_key
def test_compose_with_retry_succeeds():
    """compose_with_retry validates code and retries on failure."""
    catalog = PtoolCatalog.from_interfaces(
        [orch_double, orch_add_one],
    )
    entry_sig = _entry_signature_from_interface(orch_workflow)
    tool_interfaces = [orch_double, orch_add_one]

    def test_fn(code: str):
        pipeline = build_pipeline(code, orch_workflow, tool_interfaces)
        result = pipeline(5)
        assert result == 11

    code, attempt = compose_with_retry(
        task_description='Double the input x, then add one to the result.',
        catalog=catalog,
        entry_signature=entry_sig,
        test_fn=test_fn,
        model=ORCHESTRATOR_MODEL,
        max_retries=3,
    )

    assert attempt >= 1
    print(f'Pipeline generated on attempt {attempt}')
    print(f'Generated code:\n{code}')


@needs_together_key
def test_compose_three_step_pipeline():
    """Compose a 3-step pipeline: double, add_one, negate."""
    catalog = PtoolCatalog.from_interfaces(
        [orch_double, orch_add_one, orch_negate],
    )

    @interface
    def orch_three_step(x: int) -> int:
        """Double x, add one, then negate the result."""
        ...

    entry_sig = _entry_signature_from_interface(orch_three_step)
    tool_interfaces = [orch_double, orch_add_one, orch_negate]

    code = compose(
        task_description='Double x, then add one, then negate the result.',
        catalog=catalog,
        entry_signature=entry_sig,
        model=ORCHESTRATOR_MODEL,
    )

    pipeline = build_pipeline(code, orch_three_step, tool_interfaces)
    # double(5)=10, add_one(10)=11, negate(11)=-11
    result = pipeline(5)
    assert result == -11, f'Expected -11, got {result}'

    _INTERFACES.remove(orch_three_step)


@needs_together_key
def test_orchestrate_factory_via_implement():
    """Test OrchestrateFactory via the implement_via config path."""
    # Other tools already implemented by fixture
    orch_workflow.implement_via(
        'orchestrate',
        task_description='Double the input x, then add one to the result.',
    )

    result = orch_workflow(5)
    assert result == 11, f'Expected 11, got {result}'

    # Print the generated source
    print(f'Generated pipeline source:')
    # The factory stores the fn, we can't easily get source from here
    # but the test validates the full config-driven path works


# ── Cleanup ───────────────────────────────────────────────────────────

def teardown_module(module):
    for iface in [orch_double, orch_add_one, orch_negate, orch_workflow]:
        if iface in _INTERFACES:
            _INTERFACES.remove(iface)
