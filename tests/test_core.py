import os
import pytest
from secretagent.core import interface, implement_via, all_interfaces, _INTERFACES

needs_api_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


@interface
def sport_for(player_or_event: str) -> str:
    """Return the sport associated with a famous player."""
    ...


@pytest.fixture(autouse=True)
def reset_interfaces():
    """Reset sport_for's implementation before each test."""
    sport_for.implementation = None
    yield
    sport_for.implementation = None


def test_unbound_interface_raises():
    with pytest.raises(NotImplementedError, match='no implementation registered'):
        sport_for('Kobe Bryant')


def test_echo(capsys):
    sport_for.implement_via('echo')
    result = sport_for('Kobe Bryant')
    assert result is None


def test_all_interfaces():
    names = [i.name for i in all_interfaces()]
    assert 'sport_for' in names


def test_rebind():
    sport_for.implement_via('echo')
    sport_for.implement_via('echo', echo_doc=True)
    assert sport_for.implementation is not None
    assert sport_for.implementation.factory_kwargs == {'echo_doc': True}


def test_implement_via_decorator(capsys):
    @implement_via('echo', echo_doc=True)
    def too_long(x: str, n: int = 3) -> bool:
        """x is longer than n characters."""
        ...

    too_long("hello world")
    captured = capsys.readouterr()
    assert 'too_long' in captured.out
    assert 'x is longer than n characters' in captured.out
    _INTERFACES.remove(too_long)


def test_direct():
    @interface
    def sport_for_direct(player_or_event: str) -> str:
        """Return the sport associated with a famous player."""
        return {'Kobe Bryant': 'basketball', 'Babe Ruth': 'baseball'}[player_or_event]

    sport_for_direct.implement_via('direct')
    assert sport_for_direct('Kobe Bryant') == 'basketball'
    assert sport_for_direct('Babe Ruth') == 'baseball'
    # clean up
    _INTERFACES.remove(sport_for_direct)


def test_prompt_llm_requires_exactly_one_template():
    """Must give exactly one of prompt_template_str or prompt_template_file."""
    with pytest.raises(ValueError, match='Exactly one'):
        sport_for.implement_via('prompt_llm')
    with pytest.raises(ValueError, match='Exactly one'):
        sport_for.implement_via('prompt_llm',
                                prompt_template_str='hi',
                                prompt_template_file='foo.txt')


@needs_api_key
def test_simulate():
    sport_for.implement_via('simulate', llm = dict(model="claude-haiku-4-5-20251001"))
    result = sport_for('Kobe Bryant')
    assert isinstance(result, str)
    assert len(result) > 0
