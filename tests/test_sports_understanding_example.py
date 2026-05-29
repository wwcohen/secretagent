"""Tests for examples/sports_understanding.py."""

import pytest
from conftest import needs_api_key, CI_TEST_MODEL
from secretagent import config, record

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
    with config.configuration(llm={'model': CI_TEST_MODEL}):
        result = su.sports_understanding_workflow('Kobe Bryant scored a layup')
        assert result

        result = su.sports_understanding_workflow('LeBron James scored a touchdown')
        assert not result

@needs_api_key
def test_recording():
    su = _import_sports()
    _bind_simulate(su)
    with config.configuration(llm={'model': CI_TEST_MODEL}), record.recorder() as rollout:
        su.sports_understanding_workflow("DeMar DeRozan was called for the goal tend.")
        assert len(rollout) >= 4
        for entry in rollout:
            assert 'func' in entry
            assert 'stats' in entry
