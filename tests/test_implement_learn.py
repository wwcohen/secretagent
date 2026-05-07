import pytest
from omegaconf import OmegaConf

from secretagent import config
from secretagent.core import interface, _FACTORIES
from secretagent.implement.learnedcode import (
    _find_learned_path, _build_backoff_impl, LearnedCodeFactory,
)
from secretagent.implement.util import _find_learned_module_path


@pytest.fixture(autouse=True)
def clean_config():
    """Reset config before and after each test."""
    saved = config.GLOBAL_CONFIG.copy()
    yield
    config.GLOBAL_CONFIG = saved


def _write_learned_py(workdir, interface_name, body):
    """Write a learned.py with a simple function definition."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / 'learned.py').write_text(
        f'def {interface_name}(*args, **kw):\n'
        f'    {body}\n'
    )


def _write_source_configs(workdir, interface_name, ptools_cfg, n=1):
    """Write n identical source config yamls."""
    cfg_dir = workdir / 'source_configs'
    cfg_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        cfg = OmegaConf.create({'ptools': {interface_name: ptools_cfg}})
        (cfg_dir / f'source_{i}.yaml').write_text(OmegaConf.to_yaml(cfg))


def _make_interface(name):
    """Create a minimal interface for testing."""
    def stub(x: str) -> str:
        ...
    stub.__name__ = name
    stub.__qualname__ = name
    return interface(stub)


# --- _find_learned_path tests ---


def test_find_learned_path(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_learned_py(tmp_path / '20260101.120000.my_func__rote', 'my_func', 'return "a"')
    path = _find_learned_path('my_func', 'rote')
    assert path.name == 'learned.py'
    assert 'my_func__rote' in str(path.parent.name)


def test_find_learned_path_picks_most_recent(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_learned_py(tmp_path / '20260101.120000.my_func__rote', 'my_func', 'return "old"')
    _write_learned_py(tmp_path / '20260201.120000.my_func__rote', 'my_func', 'return "new"')
    path = _find_learned_path('my_func', 'rote')
    assert '20260201' in str(path)


def test_find_learned_path_no_match(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    with pytest.raises(FileNotFoundError):
        _find_learned_path('no_such_func', 'rote')


# --- setup/result_fn tests (no backoff) ---


def test_setup_loads_function(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_learned_py(tmp_path / '20260101.120000.my_func__rote', 'my_func', 'return "hello"')
    iface = _make_interface('my_func')
    factory = LearnedCodeFactory()
    impl = factory.build_implementation(iface, learner='rote')
    assert impl.implementing_fn('anything') == 'hello'


def test_setup_missing_function_name(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_learned_py(tmp_path / '20260101.120000.my_func__rote', 'wrong_name', 'return "hello"')
    iface = _make_interface('my_func')
    factory = LearnedCodeFactory()
    with pytest.raises(AttributeError, match='my_func'):
        factory.build_implementation(iface, learner='rote')


def test_implement_via_learned(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_learned_py(tmp_path / '20260101.120000.my_func2__rote', 'my_func2', 'return "impl"')
    iface = _make_interface('my_func2')
    iface.implement_via('learned_code', learner='rote')
    assert iface('x') == 'impl'


# --- backoff tests ---


def test_backoff_returns_learned_when_not_none(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    workdir = tmp_path / '20260101.120000.my_func3__rote'
    _write_learned_py(workdir, 'my_func3', 'return "learned"')
    _write_source_configs(workdir, 'my_func3', {'method': 'direct'})
    iface = _make_interface('my_func3')
    factory = LearnedCodeFactory()
    impl = factory.build_implementation(iface, learner='rote', backoff=True)
    fn = impl.implementing_fn
    assert fn('x') == 'learned'


def test_backoff_falls_back_when_none(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    workdir = tmp_path / '20260101.120000.my_func4__rote'
    _write_learned_py(workdir, 'my_func4', 'return None')
    _write_source_configs(workdir, 'my_func4', {'method': 'direct'})
    iface = _make_interface('my_func4')
    factory = LearnedCodeFactory()
    impl = factory.build_implementation(iface, learner='rote', backoff=True)
    fn = impl.implementing_fn
    # direct factory uses the stub body, which returns None (via ...)
    # so the backoff also returns None — but it exercises the path
    result = fn('x')
    # The stub returns None too, so result is None — the key check is no error
    assert result is None


def test_backoff_uses_direct_fn(tmp_path):
    """Backoff with direct factory pointing to a real function."""
    config.configure(learn=dict(train_dir=str(tmp_path)))
    workdir = tmp_path / '20260101.120000.my_func5__rote'
    _write_learned_py(workdir, 'my_func5', 'return None')
    _write_source_configs(workdir, 'my_func5',
                          {'method': 'direct', 'fn': 'json.loads'})
    iface = _make_interface('my_func5')
    factory = LearnedCodeFactory()
    impl = factory.build_implementation(iface, learner='rote', backoff=True)
    fn = impl.implementing_fn
    assert fn('{"a": 1}') == {'a': 1}


def test_backoff_no_fallback_when_learned_has_answer(tmp_path):
    """When learned returns a value, backoff fn is not called."""
    config.configure(learn=dict(train_dir=str(tmp_path)))
    workdir = tmp_path / '20260101.120000.my_func6__rote'
    _write_learned_py(workdir, 'my_func6', 'return "got_it"')
    _write_source_configs(workdir, 'my_func6',
                          {'method': 'direct', 'fn': 'json.loads'})
    iface = _make_interface('my_func6')
    factory = LearnedCodeFactory()
    impl = factory.build_implementation(iface, learner='rote', backoff=True)
    fn = impl.implementing_fn
    # Should return learned result, not json.loads result
    assert fn('hello') == 'got_it'


# --- _build_backoff_impl error cases ---


def test_backoff_no_source_configs(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    workdir = tmp_path / '20260101.120000.my_func7__rote'
    _write_learned_py(workdir, 'my_func7', 'return None')
    iface = _make_interface('my_func7')
    with pytest.raises(FileNotFoundError, match='source config'):
        _build_backoff_impl(iface, workdir)


def test_backoff_missing_interface_in_yaml(tmp_path):
    workdir = tmp_path / 'workdir'
    workdir.mkdir()
    cfg_dir = workdir / 'source_configs'
    cfg_dir.mkdir()
    cfg = OmegaConf.create({'ptools': {'other_func': {'method': 'direct'}}})
    (cfg_dir / 'source_0.yaml').write_text(OmegaConf.to_yaml(cfg))
    iface = _make_interface('my_func8')
    with pytest.raises(ValueError, match='no ptools.my_func8'):
        _build_backoff_impl(iface, workdir)


def test_backoff_conflicting_configs(tmp_path):
    workdir = tmp_path / 'workdir'
    workdir.mkdir()
    cfg_dir = workdir / 'source_configs'
    cfg_dir.mkdir()
    cfg1 = OmegaConf.create({'ptools': {'my_func9': {'method': 'direct'}}})
    cfg2 = OmegaConf.create({'ptools': {'my_func9': {'method': 'simulate'}}})
    (cfg_dir / 'source_0.yaml').write_text(OmegaConf.to_yaml(cfg1))
    (cfg_dir / 'source_1.yaml').write_text(OmegaConf.to_yaml(cfg2))
    iface = _make_interface('my_func9')
    with pytest.raises(ValueError, match='conflicting'):
        _build_backoff_impl(iface, workdir)


def test_backoff_consistent_configs_ok(tmp_path):
    """Multiple source configs that agree should not raise."""
    workdir = tmp_path / 'workdir'
    workdir.mkdir()
    _write_source_configs(workdir, 'my_func10', {'method': 'direct'}, n=3)
    iface = _make_interface('my_func10')
    impl = _build_backoff_impl(iface, workdir)
    assert impl.implementing_fn is not None


# --- __learned__.<attr> resolution in direct factory ---


def _write_ptools_evolved(workdir, body):
    """Write a ptools_evolved.py with a simple module-level function."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / 'ptools_evolved.py').write_text(body)


def test_find_learned_module_path_with_interface(tmp_path):
    """Original per-interface glob pattern still works for interface-scoped learners."""
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_ptools_evolved(
        tmp_path / '20260101.120000.my_func__ptool_editer',
        'def my_func(x): return x\n',
    )
    path = _find_learned_module_path(
        'ptool_editer', 'ptools_evolved.py', interface_name='my_func',
    )
    assert path.name == 'ptools_evolved.py'
    assert 'my_func__ptool_editer' in str(path.parent.name)


def test_find_learned_module_path_by_tag_only(tmp_path):
    """Tag-only mode for orch_learner-style dirs (no interface prefix)."""
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_ptools_evolved(
        tmp_path / '20260101.120000.orch_learner',
        'def calculate_medical_value(note, q): return "42"\n',
    )
    path = _find_learned_module_path('orch_learner', 'ptools_evolved.py')
    assert path.name == 'ptools_evolved.py'
    assert path.parent.name.endswith('.orch_learner')


def test_find_learned_module_path_picks_most_recent(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_ptools_evolved(
        tmp_path / '20260101.120000.orch_learner',
        'def my_fn(): return "old"\n',
    )
    _write_ptools_evolved(
        tmp_path / '20260201.120000.orch_learner',
        'def my_fn(): return "new"\n',
    )
    path = _find_learned_module_path('orch_learner', 'ptools_evolved.py')
    assert '20260201' in str(path)


def test_find_learned_module_path_no_match(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    with pytest.raises(FileNotFoundError):
        _find_learned_module_path('nobody_here', 'ptools_evolved.py')


def test_direct_factory_resolves_learned_attr(tmp_path):
    """direct factory with fn='__learned__.<attr>' loads ptools_evolved.py."""
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_ptools_evolved(
        tmp_path / '20260101.120000.orch_learner',
        'def evolved_entry(x: str) -> str:\n'
        '    return f"evolved:{x}"\n',
    )
    iface = _make_interface('some_entry')
    iface.implement_via(
        'direct', fn='__learned__.evolved_entry', learner='orch_learner',
    )
    assert iface('hi') == 'evolved:hi'


def test_direct_factory_learned_attr_requires_learner(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_ptools_evolved(
        tmp_path / '20260101.120000.orch_learner',
        'def evolved_entry(x): return x\n',
    )
    iface = _make_interface('some_entry2')
    with pytest.raises(ValueError, match='learner'):
        iface.implement_via('direct', fn='__learned__.evolved_entry')


def test_direct_factory_learned_attr_missing(tmp_path):
    config.configure(learn=dict(train_dir=str(tmp_path)))
    _write_ptools_evolved(
        tmp_path / '20260101.120000.orch_learner',
        'def evolved_entry(x): return x\n',
    )
    iface = _make_interface('some_entry3')
    with pytest.raises(AttributeError, match='does_not_exist'):
        iface.implement_via(
            'direct', fn='__learned__.does_not_exist', learner='orch_learner',
        )


def test_direct_factory_non_learned_still_works(tmp_path):
    """Non-__learned__ fn strings resolve via resolve_dotted (backwards compatible)."""
    iface = _make_interface('some_entry4')
    iface.implement_via('direct', fn='json.loads')
    assert iface('{"a": 1}') == {'a': 1}


def test_direct_factory_learned_binds_sub_interfaces(tmp_path):
    """When loading a learned module that has its own @interface-decorated
    tools, those tools' implementations should be bound from the current
    `ptools` config so the learned entry-point can call them."""
    config.configure(learn=dict(train_dir=str(tmp_path)))
    # The learned module exposes a `workflow` function that calls a tool
    # Interface `helper_tool`. With sub-binding, helper_tool gets bound
    # to a direct implementation pulled from the ptools config.
    (tmp_path / '20260101.120000.orch_learner').mkdir()
    (tmp_path / '20260101.120000.orch_learner' / 'ptools_evolved.py').write_text(
        'from secretagent.core import interface\n'
        '\n'
        '@interface\n'
        'def helper_tool(x: str) -> str:\n'
        '    """Help with x."""\n'
        '    ...\n'
        '\n'
        'def workflow(x: str) -> str:\n'
        '    return "wf:" + helper_tool(x)\n'
    )
    # Provide a ptools config that tells the resolver how to bind helper_tool.
    # json.dumps turns 'hello' into '"hello"' — deterministic and no LLM needed.
    config.configure(ptools=dict(
        helper_tool=dict(method='direct', fn='json.dumps'),
    ))
    iface = _make_interface('the_entry')
    iface.implement_via(
        'direct', fn='__learned__.workflow', learner='orch_learner',
    )
    # helper_tool was bound via sub-binding, so workflow('hello') returns 'wf:"hello"'.
    assert iface('hello') == 'wf:"hello"'
