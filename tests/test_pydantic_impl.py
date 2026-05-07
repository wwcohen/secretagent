"""Tests for secretagent.implement.pydantic."""

import pytest
from omegaconf import OmegaConf
from pydantic import BaseModel

from conftest import needs_api_key, CI_TEST_MODEL
from secretagent import config, record
from secretagent.core import interface, all_factories, _INTERFACES
from secretagent.implement.pydantic import SimulatePydanticFactory, _summarize_messages


@pytest.fixture(autouse=True)
def reset_config():
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


# --- factory registration ---

def test_simulate_pydantic_registered():
    factory_names = [name for name, _ in all_factories()]
    assert 'simulate_pydantic' in factory_names


# --- prompt generation ---

def test_create_prompt_includes_stub_and_args():
    @interface
    def greet(name: str) -> str:
        """Say hello to the named person."""

    factory = SimulatePydanticFactory()
    prompt = factory.create_prompt(greet, 'Alice')
    assert 'Say hello to the named person' in prompt
    assert "name = 'Alice'" in prompt
    _INTERFACES.remove(greet)


def test_create_prompt_without_thinking():
    @interface
    def add(a: int, b: int) -> int:
        """Add two numbers."""

    factory = SimulatePydanticFactory()
    prompt = factory.create_prompt(add, 1, 2)
    assert '<thought>' not in prompt
    _INTERFACES.remove(add)


# --- _summarize_messages ---

class _FakePart:
    def __init__(self, kind, **kw):
        self.part_kind = kind
        for k, v in kw.items():
            setattr(self, k, v)

class _FakeMsg:
    def __init__(self, parts):
        self.parts = parts


def test_summarize_messages_text():
    msgs = [_FakeMsg([_FakePart('text', content='thinking...')])]
    steps = _summarize_messages(msgs)
    assert steps == [{'thought': 'thinking...'}]


def test_summarize_messages_empty_text_skipped():
    msgs = [_FakeMsg([_FakePart('text', content='   ')])]
    steps = _summarize_messages(msgs)
    assert steps == []


def test_summarize_messages_tool_call():
    msgs = [_FakeMsg([_FakePart('tool-call', tool_name='search', args={'q': 'test'})])]
    steps = _summarize_messages(msgs)
    assert steps == [{'tool_call': 'search', 'args': {'q': 'test'}}]


def test_summarize_messages_tool_return():
    msgs = [_FakeMsg([_FakePart('tool-return', tool_name='search', content='result')])]
    steps = _summarize_messages(msgs)
    assert steps == [{'tool_return': 'search', 'output': 'result'}]


def test_summarize_messages_mixed():
    msgs = [
        _FakeMsg([
            _FakePart('text', content='let me think'),
            _FakePart('tool-call', tool_name='calc', args={'x': 1}),
        ]),
        _FakeMsg([
            _FakePart('tool-return', tool_name='calc', content='42'),
            _FakePart('text', content='done'),
        ]),
    ]
    steps = _summarize_messages(msgs)
    assert len(steps) == 4
    assert steps[0] == {'thought': 'let me think'}
    assert steps[1] == {'tool_call': 'calc', 'args': {'x': 1}}
    assert steps[2] == {'tool_return': 'calc', 'output': '42'}
    assert steps[3] == {'thought': 'done'}


# --- integration test (requires API key) ---

@needs_api_key
def test_simulate_pydantic_str():
    @interface
    def capital_of(country: str) -> str:
        """Return the capital city of the given country."""

    capital_of.implement_via('simulate_pydantic', llm={'model': CI_TEST_MODEL})
    with config.configuration(cachier={'enable_caching':False}):
        result = capital_of('France')
    assert isinstance(result, str)
    assert 'paris' in result.lower()
    _INTERFACES.remove(capital_of)


@needs_api_key
def test_simulate_pydantic_structured():

    class CityInfo(BaseModel):
        city: str
        country: str

    @interface
    def capital_info(country: str) -> CityInfo:
        """Return the capital city and country name."""

    capital_info.implement_via('simulate_pydantic', llm={'model': CI_TEST_MODEL})
    # disable caching
    with config.configuration(cachier={'enable_caching':False}):
        result = capital_info('France')
    assert isinstance(result, CityInfo)
    assert 'paris' in result.city.lower()
    _INTERFACES.remove(capital_info)


@needs_api_key
def test_simulate_pydantic_records():
    @interface
    def double(x: int) -> int:
        """Return x times 2."""

    double.implement_via('simulate_pydantic', llm={'model': CI_TEST_MODEL})
    with record.recorder() as rollout:
        with config.configuration(cachier={'enable_caching':False}):
            double(5)
    assert len(rollout) == 1
    assert rollout[0]['func'] == 'double'
    assert 'stats' in rollout[0]
    assert 'step_info' in rollout[0]
    _INTERFACES.remove(double)
