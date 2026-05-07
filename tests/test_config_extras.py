"""Tests for config.configure(dotlist=...), config.set_root(), and implement_via_config."""

import types
import pytest
from omegaconf import OmegaConf

from secretagent import config
from secretagent.core import interface, implement_via_config, _INTERFACES


@pytest.fixture(autouse=True)
def reset_config():
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


# --- config.configure(dotlist=...) ---

def test_dotlist_simple_key():
    config.configure(dotlist=["llm.model=gpt-4o"])
    assert config.get("llm.model") == "gpt-4o"


def test_dotlist_nested_key():
    config.configure(dotlist=["echo.llm_input=true"])
    assert config.get("echo.llm_input") is True


def test_dotlist_multiple_keys():
    config.configure(dotlist=["llm.model=gpt-4o", "dataset.split=test"])
    assert config.get("llm.model") == "gpt-4o"
    assert config.get("dataset.split") == "test"


def test_dotlist_empty_is_noop():
    config.configure(dotlist=[])
    assert config.get("llm.model") is None


def test_dotlist_none_is_noop():
    config.configure(dotlist=None)
    assert config.get("llm.model") is None


def test_dotlist_combined_with_kw():
    config.configure(dotlist=["llm.model=gpt-4o"], echo={"service": True})
    assert config.get("llm.model") == "gpt-4o"
    assert config.get("echo.service") is True


def test_dotlist_overrides_earlier_config():
    config.configure(llm={"model": "old-model"})
    config.configure(dotlist=["llm.model=new-model"])
    assert config.get("llm.model") == "new-model"


def test_dotlist_preserves_existing_keys():
    """Regression: configure(dotlist=...) should merge, not clobber existing config."""
    config.configure(llm={"model": "claude"}, echo={"service": True})
    config.configure(dotlist=["llm.thinking=true"])
    assert config.get("llm.model") == "claude"
    assert config.get("echo.service") is True
    assert config.get("llm.thinking") is True


# --- config.to_dotlist() ---

def test_to_dotlist_flat():
    cfg = OmegaConf.create({"a": 1, "b": "hello"})
    result = config.to_dotlist(cfg)
    assert "a=1" in result
    assert "b=hello" in result


def test_to_dotlist_nested():
    cfg = OmegaConf.create({"llm": {"model": "claude", "thinking": True}})
    result = config.to_dotlist(cfg)
    assert "llm.model=claude" in result
    assert "llm.thinking=True" in result


def test_to_dotlist_empty():
    cfg = OmegaConf.create({})
    assert config.to_dotlist(cfg) == []


# --- config.load_yaml_cfg() ---

def test_load_yaml_cfg(tmp_path):
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text(OmegaConf.to_yaml(OmegaConf.create({"llm": {"model": "claude"}})))
    loaded = config.load_yaml_cfg(cfg_file)
    assert OmegaConf.select(loaded, "llm.model") == "claude"


def test_load_yaml_cfg_missing_file(tmp_path):
    with pytest.raises(ValueError, match="expected config file"):
        config.load_yaml_cfg(tmp_path / "nonexistent.yaml")


# --- config.sanity_check() ---

def test_sanity_check_no_warning_on_valid_key():
    cfg = OmegaConf.create({"llm": {"model": "claude"}})
    # should not warn
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        config.sanity_check("test", ["llm.model=claude"], cfg)


def test_sanity_check_warns_on_unknown_key():
    cfg = OmegaConf.create({"llm": {"model": "claude"}})
    with pytest.warns(match="unexpected config key"):
        config.sanity_check("test", ["llm.nonexistent=foo"], cfg)


# --- config.set_root() ---

def test_set_root_resolves_relative_dir():
    config.configure(evaluate={"result_dir": "results"})
    config.set_root("/home/user/project")
    assert config.get("evaluate.result_dir") == "/home/user/project/results"


def test_set_root_resolves_relative_file():
    config.configure(logging={"log_file": "logs/out.log"})
    config.set_root("/home/user/project")
    assert config.get("logging.log_file") == "/home/user/project/logs/out.log"


def test_set_root_leaves_absolute_paths():
    config.configure(evaluate={"result_dir": "/absolute/path"})
    config.set_root("/home/user/project")
    assert config.get("evaluate.result_dir") == "/absolute/path"


def test_set_root_ignores_non_dir_file_keys():
    config.configure(llm={"model": "gpt-4o"})
    config.set_root("/home/user/project")
    assert config.get("llm.model") == "gpt-4o"


def test_set_root_handles_nested_sections():
    config.configure(cachier={"cache_dir": "llm_cache"}, evaluate={"result_dir": "results"})
    config.set_root("/root")
    assert config.get("cachier.cache_dir") == "/root/llm_cache"
    assert config.get("evaluate.result_dir") == "/root/results"


def test_set_root_no_double_resolve():
    """Calling set_root twice should not double-prepend."""
    config.configure(evaluate={"result_dir": "results"})
    config.set_root("/root")
    config.set_root("/root")
    assert config.get("evaluate.result_dir") == "/root/results"


# --- implement_via_config ---

def test_implement_via_config_binds_tools():
    @interface
    def greet(name: str) -> str:
        """Say hello."""
        return f"hello {name}"

    @interface
    def farewell(name: str) -> str:
        """Say goodbye."""
        return f"bye {name}"

    mod = types.ModuleType("fake_tools")
    mod.greet = greet
    mod.farewell = farewell

    tools_cfg = OmegaConf.create({
        "greet": {"method": "direct"},
        "farewell": {"method": "direct"},
    })
    implement_via_config(mod, tools_cfg)

    assert greet("Alice") == "hello Alice"
    assert farewell("Bob") == "bye Bob"
    _INTERFACES.remove(greet)
    _INTERFACES.remove(farewell)


def test_implement_via_config_passes_extra_kwargs():
    @interface
    def my_func(x: str) -> str:
        """Do something."""

    mod = types.ModuleType("fake_tools")
    mod.my_func = my_func

    tools_cfg = OmegaConf.create({
        "my_func": {"method": "direct"},
    })
    implement_via_config(mod, tools_cfg)

    assert my_func.implementation is not None
    assert my_func.implementation.factory_kwargs == {}
    _INTERFACES.remove(my_func)


def test_implement_via_config_bad_tool_name():
    mod = types.ModuleType("fake_tools")
    tools_cfg = OmegaConf.create({
        "nonexistent": {"method": "direct"},
    })
    with pytest.raises(AttributeError):
        implement_via_config(mod, tools_cfg)


def test_implement_via_config_bad_method():
    @interface
    def my_func(x: str) -> str:
        """Do something."""

    mod = types.ModuleType("fake_tools")
    mod.my_func = my_func

    tools_cfg = OmegaConf.create({
        "my_func": {"method": "nonexistent_method"},
    })
    with pytest.raises(KeyError):
        implement_via_config(mod, tools_cfg)
    _INTERFACES.remove(my_func)
