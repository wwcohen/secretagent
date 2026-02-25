import os
import pytest
from secretagent.ptool import ptool, implement_via, _REGISTRY
from secretagent.ptool import list as ptool_list

needs_api_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


@ptool()
def sport_for(player_or_event: str) -> str:
    """Return the sport associated with a famous player."""
    ...


@pytest.fixture(autouse=True)
def reset_registry():
    """Remove sport_for from registry before each test."""
    _REGISTRY.pop("sport_for", None)
    yield
    _REGISTRY.pop("sport_for", None)


def test_unbound_ptool_raises():
    with pytest.raises(NotImplementedError, match='no implementation registered'):
        sport_for('Kobe Bryant')


def test_echo(capsys):
    implement_via(sport_for, 'echo')
    result = sport_for('Kobe Bryant')
    assert result is None


def test_list_empty():
    assert ptool_list() == []


def test_list_after_echo():
    implement_via(sport_for, 'echo')
    entries = ptool_list()
    assert len(entries) == 1
    assert entries[0]['name'] == 'sport_for'
    assert entries[0]['method'] == 'echo'


def test_list_after_rebind():
    implement_via(sport_for, 'echo')
    implement_via(sport_for, 'echo', echo_goal=True)
    entries = ptool_list()
    assert len(entries) == 1
    assert entries[0]['kwargs'] == {'echo_goal': True}


@needs_api_key
def test_rebind_to_simulate_from_stub():
    implement_via(sport_for, 'simulate_from_stub', model="claude-haiku-4-5-20251001")
    result = sport_for('Kobe Bryant')
    assert isinstance(result, str)
    assert len(result) > 0
