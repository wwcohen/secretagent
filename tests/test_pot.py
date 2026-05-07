"""Tests for PoTFactory (program_of_thought)."""

import pytest
from omegaconf import OmegaConf

from conftest import needs_api_key, CI_TEST_MODEL
from secretagent import config, record
from secretagent.core import interface, all_factories, _INTERFACES
from secretagent.implement.core import PoTFactory


@pytest.fixture(autouse=True)
def reset_config():
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


# --- factory registration ---

def test_pot_factory_registered():
    factory_names = [name for name, _ in all_factories()]
    assert 'program_of_thought' in factory_names


# --- prompt generation ---

def test_create_prompt_includes_stub_and_args():
    @interface
    def add(a: int, b: int) -> int:
        """Add two numbers."""

    add.implement_via('direct')

    @interface
    def compute(x: int) -> int:
        """Compute something using add."""

    factory = PoTFactory()
    prompt = factory.create_prompt(compute, [add], None, 5)
    assert 'Compute something using add' in prompt
    assert "x = 5" in prompt
    # tool stubs should be listed
    assert 'add' in prompt
    _INTERFACES.remove(add)
    _INTERFACES.remove(compute)


def test_create_prompt_includes_tool_stubs():
    @interface
    def helper(x: str) -> str:
        """A helper tool."""

    helper.implement_via('direct')

    @interface
    def main_fn(s: str) -> str:
        """Main function that uses helper."""

    factory = PoTFactory()
    prompt = factory.create_prompt(main_fn, [helper], None, "test")
    assert 'A helper tool' in prompt
    # main_fn's own stub should not be in tool listing
    assert prompt.count('Main function that uses helper') == 1
    _INTERFACES.remove(helper)
    _INTERFACES.remove(main_fn)


def test_create_prompt_includes_pydantic_tool_schema():
    from pydantic import BaseModel

    class ToolResult(BaseModel):
        verdict: bool
        detail: str

    @interface
    def my_tool(q: str) -> ToolResult:
        """A tool returning a pydantic model."""

    my_tool.implement_via('direct')

    @interface
    def caller(q: str) -> str:
        """Calls my_tool."""

    factory = PoTFactory()
    prompt = factory.create_prompt(caller, [my_tool], None, "test")
    assert 'ToolResult' in prompt
    assert '"verdict"' in prompt
    assert '"type": "boolean"' in prompt
    assert '"detail"' in prompt
    _INTERFACES.remove(my_tool)
    _INTERFACES.remove(caller)


def test_create_prompt_mentions_final_answer():
    @interface
    def my_fn(x: int) -> int:
        """Double x."""

    factory = PoTFactory()
    prompt = factory.create_prompt(my_fn, [], None, 3)
    assert 'final_answer' in prompt
    _INTERFACES.remove(my_fn)


def test_create_prompt_without_thinking():
    @interface
    def my_fn(x: int) -> int:
        """Double x."""

    factory = PoTFactory()
    prompt = factory.create_prompt(my_fn, [], None, 3)
    assert '<thought>' not in prompt
    _INTERFACES.remove(my_fn)


def test_create_prompt_with_thinking():
    config.configure(llm={'thinking': True})

    @interface
    def my_fn(x: int) -> int:
        """Double x."""

    factory = PoTFactory()
    prompt = factory.create_prompt(my_fn, [], None, 3)
    assert '<thought>' in prompt
    _INTERFACES.remove(my_fn)


# --- executor wiring ---

def test_executor_has_tool_functions():
    """Tools bound before PoT should appear in the executor's custom_tools."""
    @interface
    def tool_a(x: int) -> int:
        """Return x + 1."""
        return x + 1

    tool_a.implement_via('direct')

    @interface
    def orchestrator(x: int) -> int:
        """Use tool_a."""

    factory = PoTFactory()
    impl = factory.build_implementation(orchestrator)
    assert callable(impl.implementing_fn)
    _INTERFACES.remove(tool_a)
    _INTERFACES.remove(orchestrator)


# --- state isolation ---

def test_tool_redefinition_does_not_poison_custom_tools():
    """Regression: LLM-generated code that redefines a tool as a stub must not
    permanently overwrite the real tool in custom_tools (GitHub issue: PoT
    scores 2.2% on NBA because tool wrappers get replaced with Ellipsis)."""
    from smolagents.local_python_executor import LocalPythonExecutor, BASE_PYTHON_TOOLS

    real_tool = lambda x: x * 2
    executor = LocalPythonExecutor(additional_authorized_imports=[])
    executor.static_tools = {**BASE_PYTHON_TOOLS, "final_answer": lambda x: x}
    executor.custom_tools = {"my_tool": real_tool}

    poisoning_code = (
        "def my_tool(x):\n"
        "    ...\n"
        "result = my_tool(5)\n"
        "final_answer(result)\n"
    )

    saved = dict(executor.custom_tools)
    executor.state = {}
    result1 = executor(poisoning_code)
    assert result1.output is ...
    executor.custom_tools = saved

    clean_code = "result = my_tool(5)\nfinal_answer(result)\n"
    executor.state = {}
    result2 = executor(clean_code)
    assert result2.output == 10, (
        f"Tool was poisoned: expected 10 but got {result2.output}"
    )


def test_state_does_not_leak_between_calls():
    """Variables assigned in one PoT execution must not be visible in the next."""
    from smolagents.local_python_executor import LocalPythonExecutor, BASE_PYTHON_TOOLS

    executor = LocalPythonExecutor(additional_authorized_imports=[])
    executor.static_tools = {**BASE_PYTHON_TOOLS, "final_answer": lambda x: x}
    executor.custom_tools = {}

    executor.state = {}
    executor("leaked_var = 42\nfinal_answer(leaked_var)\n")

    executor.state = {}
    with pytest.raises(Exception):
        executor("final_answer(leaked_var)\n")


# --- integration tests (require API key) ---

@needs_api_key
def test_pot_simple_tool_call():
    """PoT should generate code that calls tools and returns a result."""
    @interface
    def double(x: int) -> int:
        """Return x times 2."""
        return x * 2

    double.implement_via('direct')

    @interface
    def quadruple(x: int) -> int:
        """Return x times 4 by calling double twice."""

    quadruple.implement_via('program_of_thought',
                            llm={'model': CI_TEST_MODEL})
    with config.configuration(cachier={'enable_caching': False}):
        result = quadruple(3)
    assert result == 12
    _INTERFACES.remove(double)
    _INTERFACES.remove(quadruple)


@needs_api_key
def test_pot_records_generated_code():
    """PoT should record the generated code in the rollout."""
    @interface
    def inc(x: int) -> int:
        """Return x + 1."""
        return x + 1

    inc.implement_via('direct')

    @interface
    def add_two(x: int) -> int:
        """Return x + 2 by calling inc twice."""

    add_two.implement_via('program_of_thought',
                          llm={'model': CI_TEST_MODEL})
    with config.configuration(cachier={'enable_caching': False}):
        with record.recorder() as rollout:
            add_two(5)
    pot_entries = [r for r in rollout if r['func'] == 'add_two']
    assert len(pot_entries) == 1
    assert 'step_info' in pot_entries[0]
    assert 'inc' in pot_entries[0]['step_info']['generated_code']
    assert 'final_answer' in pot_entries[0]['step_info']['generated_code']
    _INTERFACES.remove(inc)
    _INTERFACES.remove(add_two)
