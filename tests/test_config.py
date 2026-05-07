import pytest
from omegaconf import OmegaConf
from secretagent import config


@pytest.fixture(autouse=True)
def reset_global_config():
    """Reset GLOBAL_CONFIG before each test."""
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


# --- configure() ---

def test_configure_sets_flat_values():
    config.configure(llm={'model': 'claude'})
    assert config.GLOBAL_CONFIG.llm.model == 'claude'


def test_configure_merges():
    config.configure(llm={'model': 'claude'})
    config.configure(echo={'model': True})
    assert config.GLOBAL_CONFIG.llm.model == 'claude'
    assert config.GLOBAL_CONFIG.echo.model is True


def test_configure_overwrites_key():
    config.configure(llm={'model': 'claude'})
    config.configure(llm={'model': 'gpt-4'})
    assert config.GLOBAL_CONFIG.llm.model == 'gpt-4'


# --- get() ---

def test_get_dot_notation():
    config.configure(llm={'model': 'claude'})
    assert config.get('llm.model') == 'claude'


def test_get_missing_key_returns_none():
    assert config.get('nonexistent') is None


def test_get_with_default():
    assert config.get('nonexistent', 'fallback') == 'fallback'


def test_get_ignores_default_when_key_exists():
    config.configure(llm={'model': 'claude'})
    assert config.get('llm.model', 'fallback') == 'claude'


def test_get_nested_missing_returns_default():
    config.configure(llm={'model': 'claude'})
    assert config.get('llm.thinking', False) is False


# --- configuration() context manager ---

def test_configuration_applies_overrides():
    config.configure(llm={'model': 'claude'})
    with config.configuration(llm={'model': 'gpt-4'}) as cfg:
        assert cfg.llm.model == 'gpt-4'


def test_configuration_restores_on_exit():
    config.configure(llm={'model': 'claude'})
    with config.configuration(llm={'model': 'gpt-4'}):
        pass
    assert config.GLOBAL_CONFIG.llm.model == 'claude'


def test_configuration_adds_new_keys_temporarily():
    config.configure(llm={'model': 'claude'})
    with config.configuration(echo={'call': True}):
        assert config.GLOBAL_CONFIG.echo.call is True
    assert config.get('echo.call') is None


def test_configuration_nesting():
    config.configure(llm={'model': 'claude'})
    with config.configuration(llm={'model': 'gpt-4'}):
        with config.configuration(llm={'model': 'gemini'}):
            assert config.GLOBAL_CONFIG.llm.model == 'gemini'
        assert config.GLOBAL_CONFIG.llm.model == 'gpt-4'
    assert config.GLOBAL_CONFIG.llm.model == 'claude'


def test_configuration_yields_live_config():
    with config.configuration(llm={'model': 'claude'}) as cfg:
        assert cfg is config.GLOBAL_CONFIG
