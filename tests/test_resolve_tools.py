"""Tests for resolve_dotted and resolve_tools utilities."""

import pytest
from omegaconf import OmegaConf

from secretagent import config
from secretagent.core import interface, _INTERFACES
from secretagent.implement.util import resolve_dotted, resolve_tools


@pytest.fixture(autouse=True)
def reset_config():
    config.GLOBAL_CONFIG = OmegaConf.create()
    yield
    config.GLOBAL_CONFIG = OmegaConf.create()


# --- resolve_dotted ---

def test_resolve_dotted_stdlib():
    """Resolves a dotted name from the standard library."""
    result = resolve_dotted('os.path.join')
    import os.path
    assert result is os.path.join


def test_resolve_dotted_module():
    """Resolves a top-level module."""
    result = resolve_dotted('os')
    import os
    assert result is os


def test_resolve_dotted_nested():
    """Resolves a nested attribute."""
    result = resolve_dotted('os.path.sep')
    import os.path
    assert result == os.path.sep


def test_resolve_dotted_bad_module():
    with pytest.raises(ModuleNotFoundError):
        resolve_dotted('nonexistent_module_xyz.foo')


def test_resolve_dotted_bad_attr():
    with pytest.raises(AttributeError):
        resolve_dotted('os.nonexistent_attribute_xyz')


# --- resolve_tools ---

def test_resolve_tools_none():
    """None returns an empty list."""
    @interface
    def dummy(x: int) -> int:
        """Dummy."""

    assert resolve_tools(dummy, None) == []
    _INTERFACES.remove(dummy)


def test_resolve_tools_empty_list():
    """Empty list returns an empty list."""
    @interface
    def dummy(x: int) -> int:
        """Dummy."""

    assert resolve_tools(dummy, []) == []
    _INTERFACES.remove(dummy)


def test_resolve_tools_all():
    """'__all__' returns all implemented interfaces except the given one."""
    @interface
    def tool_a(x: int) -> int:
        """Tool A."""
        return x + 1

    tool_a.implement_via('direct')

    @interface
    def tool_b(x: int) -> int:
        """Tool B."""
        return x + 2

    tool_b.implement_via('direct')

    @interface
    def main_fn(x: int) -> int:
        """Main."""

    resolved = resolve_tools(main_fn, '__all__')
    # should include wrappers for tool_a and tool_b
    names = [fn.__name__ for fn in resolved]
    assert 'tool_a' in names
    assert 'tool_b' in names
    # wrappers should delegate to the interface implementations
    assert any(fn(5) == 6 for fn in resolved)   # tool_a: x+1
    assert any(fn(5) == 7 for fn in resolved)   # tool_b: x+2
    # should not include main_fn (unimplemented, and it's the excluded interface)
    _INTERFACES.remove(tool_a)
    _INTERFACES.remove(tool_b)
    _INTERFACES.remove(main_fn)


def test_resolve_tools_all_excludes_self():
    """'__all__' excludes the interface itself even if implemented."""
    @interface
    def self_fn(x: int) -> int:
        """Self."""
        return x

    self_fn.implement_via('direct')

    resolved = resolve_tools(self_fn, '__all__')
    assert 'self_fn' not in [fn.__name__ for fn in resolved]
    _INTERFACES.remove(self_fn)


def test_resolve_tools_with_interface():
    """An Interface in the list is resolved to its implementing function."""
    @interface
    def tool_a(x: int) -> int:
        """Tool A."""
        return x + 1

    tool_a.implement_via('direct')

    @interface
    def main_fn(x: int) -> int:
        """Main."""

    resolved = resolve_tools(main_fn, [tool_a])
    assert len(resolved) == 1
    assert resolved[0].__name__ == 'tool_a'
    assert resolved[0](5) == 6
    _INTERFACES.remove(tool_a)
    _INTERFACES.remove(main_fn)


def test_resolve_tools_with_callable():
    """A plain callable is passed through as-is."""
    def my_func(x):
        return x

    @interface
    def main_fn(x: int) -> int:
        """Main."""

    resolved = resolve_tools(main_fn, [my_func])
    assert resolved == [my_func]
    _INTERFACES.remove(main_fn)


def test_resolve_tools_with_string():
    """A dotted string is resolved via resolve_dotted."""
    @interface
    def main_fn(x: int) -> int:
        """Main."""

    resolved = resolve_tools(main_fn, ['os.path.join'])
    import os.path
    assert resolved == [os.path.join]
    _INTERFACES.remove(main_fn)


def test_resolve_tools_mixed():
    """A list with mixed types (Interface, callable, string) all resolve."""
    @interface
    def tool_a(x: int) -> int:
        """Tool A."""
        return x + 1

    tool_a.implement_via('direct')

    def my_func(x):
        return x

    @interface
    def main_fn(x: int) -> int:
        """Main."""

    import os.path
    resolved = resolve_tools(main_fn, [tool_a, my_func, 'os.path.join'])
    assert len(resolved) == 3
    assert resolved[0].__name__ == 'tool_a'
    assert resolved[1] is my_func
    assert resolved[2] is os.path.join
    _INTERFACES.remove(tool_a)
    _INTERFACES.remove(main_fn)


def test_resolve_tools_string_resolving_to_interface():
    """A string that resolves to an Interface yields the implementing function."""
    @interface
    def tool_iface(x: int) -> int:
        """A tool."""
        return x + 1

    tool_iface.implement_via('direct')

    # stash it on the module so resolve_dotted can find it
    import tests.test_resolve_tools as this_module
    this_module._tool_iface_for_test = tool_iface

    @interface
    def main_fn(x: int) -> int:
        """Main."""

    resolved = resolve_tools(main_fn, ['tests.test_resolve_tools._tool_iface_for_test'])
    assert len(resolved) == 1
    assert resolved[0].__name__ == 'tool_iface'
    assert resolved[0](5) == 6
    del this_module._tool_iface_for_test
    _INTERFACES.remove(tool_iface)
    _INTERFACES.remove(main_fn)


def test_resolve_tools_string_bad_name():
    """A bad dotted string raises an error."""
    @interface
    def main_fn(x: int) -> int:
        """Main."""

    with pytest.raises((ModuleNotFoundError, AttributeError)):
        resolve_tools(main_fn, ['nonexistent_module_xyz.foo'])
    _INTERFACES.remove(main_fn)


def test_resolve_tools_rejects_non_callable():
    """A non-callable value (e.g. an int) raises ValueError."""
    @interface
    def main_fn(x: int) -> int:
        """Main."""

    with pytest.raises(ValueError, match='not callable'):
        resolve_tools(main_fn, [42])
    _INTERFACES.remove(main_fn)


def test_simulate_pydantic_rejects_factory_as_tool():
    """SimulatePydanticFactory.setup rejects non-function callables like Factory instances."""
    from secretagent.core import Implementation
    from secretagent.implement.pydantic import SimulatePydanticFactory

    @interface
    def main_fn(x: int) -> int:
        """Main."""

    # A Factory instance is callable but not a function
    non_fn = Implementation.Factory()
    with pytest.raises(ValueError, match='not a function'):
        main_fn.implement_via('simulate_pydantic', tools=[non_fn])

    _INTERFACES.remove(main_fn)
