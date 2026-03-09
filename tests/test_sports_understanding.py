"""Tests for examples/sports_understanding.py."""

import os
import pytest
from secretagent import config, record

needs_api_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

def _import_sports():
    import importlib
    import examples.sports_understanding as su
    importlib.reload(su)
    return su

def _bind_simulate(su):
    """Bind all three interfaces to 'simulate'."""
    su.analyze_sentence.implement_via('simulate')
    su.sport_for.implement_via('simulate')
    su.consistent_sports.implement_via('simulate')

@needs_api_key
def test_workflow():
    su = _import_sports()
    _bind_simulate(su)
    with config.configuration(llm={'model': "claude-haiku-4-5-20251001"}):
        result = su.sports_understanding_workflow('Kobe Bryant scored a layup')
        assert result

        result = su.sports_understanding_workflow('Santi Cazorla scored a touchdown')
        assert not result

@needs_api_key
def test_recording():
    su = _import_sports()
    _bind_simulate(su)
    with config.configuration(llm={'model': "claude-haiku-4-5-20251001"}), record.recorder() as rollout:
        su.sports_understanding_workflow("DeMar DeRozan was called for the goal tend.")
        assert len(rollout) >= 4
        for entry in rollout:
            assert 'func' in entry
            assert 'stats' in entry
