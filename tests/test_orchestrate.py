"""Unit tests for the orchestrate package.

These tests don't need an API key — they test catalog, pipeline, and
code extraction logic with mock data.
"""

import pytest
from secretagent.core import interface, _INTERFACES
from secretagent.orchestrate.catalog import PtoolCatalog, PtoolInfo, _type_name
from secretagent.orchestrate.composer import _extract_code, _strip_def_line
from secretagent.orchestrate.pipeline import Pipeline, build_pipeline, _entry_signature_from_interface


# ── Test fixtures: toy interfaces ──────────────────────────────────────

@interface
def double(x: int) -> int:
    """Double the input value."""
    return x * 2

@interface
def add_one(x: int) -> int:
    """Add one to the input value."""
    return x + 1

@interface
def unimplemented_tool(x: str) -> str:
    """This tool has no implementation."""
    ...


@pytest.fixture(autouse=True)
def setup_and_cleanup():
    """Implement test interfaces, then clean up."""
    double.implement_via('direct')
    add_one.implement_via('direct')
    unimplemented_tool.implementation = None
    yield
    double.implementation = None
    add_one.implementation = None
    unimplemented_tool.implementation = None


# ── Catalog tests ──────────────────────────────────────────────────────

def test_catalog_from_interfaces_filters_unimplemented():
    catalog = PtoolCatalog.from_interfaces(
        [double, add_one, unimplemented_tool]
    )
    assert 'double' in catalog.names
    assert 'add_one' in catalog.names
    assert 'unimplemented_tool' not in catalog.names


def test_catalog_from_interfaces_include_unimplemented():
    catalog = PtoolCatalog.from_interfaces(
        [double, unimplemented_tool], include_unimplemented=True
    )
    assert 'unimplemented_tool' in catalog.names


def test_catalog_from_interfaces_excludes_by_name():
    catalog = PtoolCatalog.from_interfaces(
        [double, add_one], exclude=['double']
    )
    assert catalog.names == ['add_one']


def test_catalog_render_contains_stub_source():
    catalog = PtoolCatalog.from_interfaces([double, add_one])
    rendered = catalog.render()
    assert 'def double(x: int) -> int:' in rendered
    assert 'Double the input value' in rendered
    assert 'def add_one(x: int) -> int:' in rendered


def test_catalog_len():
    catalog = PtoolCatalog.from_interfaces([double, add_one])
    assert len(catalog) == 2


def test_catalog_repr():
    catalog = PtoolCatalog.from_interfaces([double])
    assert 'double' in repr(catalog)


def test_ptool_info_fields():
    catalog = PtoolCatalog.from_interfaces([double])
    info = catalog.ptools[0]
    assert info.name == 'double'
    assert info.param_names == ['x']
    assert info.param_types == {'x': 'int'}
    assert info.return_type == 'int'
    # V2 metric fields default to None
    assert info.avg_cost is None
    assert info.success_rate is None


def test_type_name_builtin():
    assert _type_name(int) == 'int'
    assert _type_name(str) == 'str'


def test_type_name_generic():
    # Generic types like list[str] don't have __name__
    assert 'list' in _type_name(list[str])


# ── Code extraction tests ─────────────────────────────────────────────

def test_extract_code_single_block():
    text = 'Here is the code:\n```python\nresult = double(x)\nreturn result\n```'
    assert _extract_code(text) == 'result = double(x)\nreturn result'


def test_extract_code_multiple_blocks():
    text = (
        'Draft:\n```python\nresult = x\n```\n'
        'Refined:\n```python\nresult = double(x)\nreturn result\n```'
    )
    # Takes the last block
    assert _extract_code(text) == 'result = double(x)\nreturn result'


def test_extract_code_no_block_raises():
    with pytest.raises(ValueError, match='No.*code block found'):
        _extract_code('Here is some text without code.')


# ── Strip def line tests ──────────────────────────────────────────────

def test_strip_def_line_removes_def():
    code = 'def my_func(x: int) -> int:\n    return x * 2'
    sig = 'def my_func(x: int) -> int:'
    result = _strip_def_line(code, sig)
    assert result == 'return x * 2'


def test_strip_def_line_no_def():
    code = 'result = double(x)\nreturn result'
    sig = 'def my_func(x: int) -> int:'
    result = _strip_def_line(code, sig)
    assert result == code


# ── Pipeline tests ────────────────────────────────────────────────────

def test_pipeline_compile_simple():
    code = 'return a + b'
    sig = 'def add(a: int, b: int) -> int:'
    pipeline = Pipeline(code, sig, {})
    assert pipeline(3, 4) == 7


def test_pipeline_compile_multiline():
    code = 'x = a * 2\ny = x + b\nreturn y'
    sig = 'def compute(a: int, b: int) -> int:'
    pipeline = Pipeline(code, sig, {})
    assert pipeline(3, 1) == 7  # 3*2 + 1


def test_pipeline_with_tools():
    """Generated code that calls tool functions in its namespace."""
    code = 'result = my_double(x)\nreturn result'
    sig = 'def workflow(x: int) -> int:'
    namespace = {'my_double': lambda x: x * 2}
    pipeline = Pipeline(code, sig, namespace)
    assert pipeline(5) == 10


def test_pipeline_with_interface_tools():
    """Generated code that calls Interface objects in the namespace."""
    code = 'result = double(x)\nresult = add_one(result)\nreturn result'
    sig = 'def workflow(x: int) -> int:'
    namespace = {'double': double, 'add_one': add_one}
    pipeline = Pipeline(code, sig, namespace)
    assert pipeline(5) == 11  # double(5)=10, add_one(10)=11


def test_pipeline_source_property():
    code = 'return a + b'
    sig = 'def add(a: int, b: int) -> int:'
    pipeline = Pipeline(code, sig, {})
    source = pipeline.source
    assert source.startswith('def add(a: int, b: int) -> int:')
    assert 'return a + b' in source


def test_pipeline_syntax_error():
    with pytest.raises(SyntaxError):
        Pipeline('return (', 'def f() -> int:', {})


# ── build_pipeline tests ─────────────────────────────────────────────

@interface
def double_then_add(x: int) -> int:
    """Double x then add one."""
    ...

def test_build_pipeline():
    code = 'result = double(x)\nreturn add_one(result)'
    pipeline = build_pipeline(code, double_then_add, [double, add_one])
    assert pipeline(5) == 11  # double(5)=10, add_one(10)=11
    _INTERFACES.remove(double_then_add)


# ── entry_signature_from_interface tests ──────────────────────────────

def test_entry_signature_from_interface():
    sig = _entry_signature_from_interface(double)
    assert sig == 'def double(x: int) -> int:'


# ── Cleanup: remove test interfaces from global registry ─────────────

def teardown_module(module):
    """Remove test interfaces from the global registry."""
    for iface in [double, add_one, unimplemented_tool]:
        if iface in _INTERFACES:
            _INTERFACES.remove(iface)
