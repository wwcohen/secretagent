"""Tests for PTPFactory (program trace prompting)."""

import pytest
from omegaconf import OmegaConf
from pydantic import BaseModel

from secretagent import config
from secretagent.core import interface, all_factories, _INTERFACES
from secretagent.implement.ptp import PTPFactory


@pytest.fixture(autouse=True)
def reset_config():
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


def test_ptp_factory_registered():
    assert 'ptp' in [name for name, _ in all_factories()]


def test_create_prompt_includes_traces_and_stub():
    """Regression: create_prompt must not raise KeyError on the $schema_block
    placeholder that simulate.txt requires (PTP previously omitted it, so
    every PTP call crashed in Template.substitute)."""
    @interface
    def my_fn(x: int) -> int:
        """Double x."""

    factory = PTPFactory()
    factory.traces_text = "TRACE: my_fn(x=2) -> 4"
    prompt = factory.create_prompt(my_fn, 3)  # must not raise

    assert "TRACE: my_fn(x=2) -> 4" in prompt   # traces injected as examples
    assert "Double x." in prompt                # stub docstring present
    _INTERFACES.remove(my_fn)


def test_create_prompt_includes_pydantic_schema_block():
    """For a pydantic return type, the schema block (the missing placeholder
    that crashed PTP) is rendered with the model's fields."""
    class Verdict(BaseModel):
        label: str
        score: float

    @interface
    def classify(text: str) -> Verdict:
        """Classify text."""

    factory = PTPFactory()
    prompt = factory.create_prompt(classify, "hello")  # must not raise

    assert "Verdict" in prompt
    assert "label" in prompt
    assert "score" in prompt
    _INTERFACES.remove(classify)


def test_create_prompt_plain_return_has_empty_schema_block():
    """A non-pydantic return type yields an empty schema block, and the
    prompt still builds."""
    @interface
    def my_fn(x: int) -> int:
        """Double x."""

    factory = PTPFactory()
    prompt = factory.create_prompt(my_fn, 7)  # must not raise
    assert "Double x." in prompt
    _INTERFACES.remove(my_fn)