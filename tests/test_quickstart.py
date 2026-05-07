"""Tests for examples/quickstart.py."""

import pytest
from pydantic import BaseModel
from conftest import needs_anthropic_key
from secretagent.core import _INTERFACES
from secretagent import config

# Keep track of interfaces created by imports so we can clean up
_before = set(id(i) for i in _INTERFACES)


def _cleanup_quickstart_interfaces():
    """Remove interfaces added by importing quickstart."""
    _INTERFACES[:] = [i for i in _INTERFACES if id(i) in _before]


@pytest.fixture(autouse=True)
def cleanup():
    yield
    _cleanup_quickstart_interfaces()


def _import_quickstart():
    """Import quickstart module freshly (side-effect: registers interfaces)."""
    import importlib
    import examples.quickstart as qs
    importlib.reload(qs)
    return qs


def test_quickstart_interfaces_registered():
    """Importing quickstart registers translate and translate_structured."""
    qs = _import_quickstart()
    assert hasattr(qs, 'translate')
    assert hasattr(qs, 'translate_structured')
    assert qs.translate.name == 'translate'
    assert qs.translate_structured.name == 'translate_structured'


def test_quickstart_translate_not_bound_at_import():
    """translate should not be bound after import (bound in __main__ only)."""
    qs = _import_quickstart()
    assert qs.translate.implementation is None


def test_quickstart_translate_structured_not_bound_at_import():
    """translate_structured should not be bound after import (bound in __main__ only)."""
    qs = _import_quickstart()
    assert qs.translate_structured.implementation is None


def test_quickstart_translate_structured_return_type():
    """translate_structured should have FrenchEnglishTranslation as return type."""
    qs = _import_quickstart()
    ret_type = qs.translate_structured.annotations.get('return')
    assert ret_type is not None
    assert issubclass(ret_type, BaseModel)
    assert ret_type.__name__ == 'FrenchEnglishTranslation'


def _reasonable(french_translation: str) -> bool:
    if 'bonjour' not in french_translation.lower():
        return False
    if 'comment allez' not in french_translation.lower():
        return False        
    return True

@needs_anthropic_key
def test_quickstart_translate_returns_reasonable_string():
    """translate should return a non-empty string."""
    qs = _import_quickstart()
    qs.translate.implement_via('simulate', llm={'model': qs.DEFAULT_MODEL})
    with config.configuration(cachier={'enable_caching':False}):
        result = qs.translate("Hello, how are you?")
    assert isinstance(result, str)
    assert len(result) > 0
    assert _reasonable(result)


@needs_anthropic_key
def test_quickstart_translate_structured_returns_reasonable_model():
    """translate_structured should return a FrenchEnglishTranslation."""
    qs = _import_quickstart()
    qs.translate_structured.implement_via('simulate_pydantic', llm={'model': qs.DEFAULT_MODEL})
    with config.configuration(cachier={'enable_caching':False}):
        result = qs.translate_structured("Hello, how are you?")
    assert isinstance(result, qs.FrenchEnglishTranslation)
    assert isinstance(result.english_text, str)
    assert isinstance(result.french_text, str)
    assert _reasonable(result.french_text)
