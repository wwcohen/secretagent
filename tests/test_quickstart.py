"""Tests for examples/quickstart.py."""

import os
import pytest
from pydantic import BaseModel
from secretagent.core import _INTERFACES

needs_api_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

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


def test_quickstart_translate_has_implementation():
    """translate should be bound to simulate after import."""
    qs = _import_quickstart()
    assert qs.translate.implementation is not None


def test_quickstart_translate_structured_has_implementation():
    """translate_structured should be bound to simulate_pydantic after import."""
    qs = _import_quickstart()
    assert qs.translate_structured.implementation is not None


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

@needs_api_key
def test_quickstart_translate_returns_reasonable_string():
    """translate should return a non-empty string."""
    qs = _import_quickstart()
    result = qs.translate("Hello, how are you?")
    assert isinstance(result, str)
    assert len(result) > 0
    assert _reasonable(result)


@needs_api_key
def test_quickstart_translate_structured_returns_reasonable_model():
    """translate_structured should return a FrenchEnglishTranslation."""
    qs = _import_quickstart()
    result = qs.translate_structured("Hello, how are you?")
    assert isinstance(result, qs.FrenchEnglishTranslation)
    assert isinstance(result.english_text, str)
    assert isinstance(result.french_text, str)
    assert _reasonable(result.french_text)
