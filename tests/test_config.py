import pytest
from secretagent import config


@pytest.fixture(autouse=True)
def reset_global_config():
    """Reset GLOBAL_CONFIG before each test."""
    config.GLOBAL_CONFIG = {}
    yield
    config.GLOBAL_CONFIG = {}


# --- configure() ---

def test_configure_sets_values():
    config.configure(service="anthropic", model="claude")
    assert config.GLOBAL_CONFIG == {"service": "anthropic", "model": "claude"}


def test_configure_updates_existing():
    config.configure(service="anthropic")
    config.configure(model="claude")
    assert config.GLOBAL_CONFIG == {"service": "anthropic", "model": "claude"}


def test_configure_overwrites_key():
    config.configure(service="anthropic")
    config.configure(service="openai")
    assert config.GLOBAL_CONFIG["service"] == "openai"


# --- get() ---

def test_get_from_global():
    config.configure(service="anthropic")
    assert config.get("service") == "anthropic"


def test_get_missing_key_returns_none():
    assert config.get("nonexistent") is None


def test_get_local_overrides_global():
    config.configure(service="anthropic")
    local = {"service": "openai"}
    assert config.get("service", local) == "openai"


def test_get_falls_back_to_global():
    config.configure(model="claude")
    local = {"service": "openai"}
    assert config.get("model", local) == "claude"


def test_get_empty_local_uses_global():
    config.configure(service="anthropic")
    assert config.get("service", {}) == "anthropic"


# --- configuration() context manager ---

def test_configuration_applies_overrides():
    config.configure(service="anthropic")
    with config.configuration(service="openai") as cfg:
        assert cfg["service"] == "openai"


def test_configuration_restores_on_exit():
    config.configure(service="anthropic", model="claude")
    with config.configuration(service="openai"):
        pass
    assert config.GLOBAL_CONFIG == {"service": "anthropic", "model": "claude"}


def test_configuration_adds_new_keys_temporarily():
    config.configure(service="anthropic")
    with config.configuration(echo_call=True):
        assert config.GLOBAL_CONFIG["echo_call"] is True
    assert "echo_call" not in config.GLOBAL_CONFIG


def test_configuration_nesting():
    config.configure(service="anthropic")
    with config.configuration(service="openai"):
        with config.configuration(service="gemini"):
            assert config.GLOBAL_CONFIG["service"] == "gemini"
        assert config.GLOBAL_CONFIG["service"] == "openai"
    assert config.GLOBAL_CONFIG["service"] == "anthropic"


def test_configuration_yields_live_config():
    with config.configuration(service="anthropic") as cfg:
        assert cfg is config.GLOBAL_CONFIG
