"""Unit tests for OrchestrationLearner.

These tests exercise the Learner framework plumbing — directory layout,
implementation.yaml shape, resume semantics — without invoking the supervisor
LLM or running a benchmark. `fit()` is monkeypatched out; the rest of the
class's behavior is exercised directly.
"""

import json
from pathlib import Path

import pytest
import yaml

from secretagent import config
from secretagent.learn import orchestrate_learner as orch_mod
from secretagent.learn.orchestrate_learner import (
    OrchestrationLearner, LEARNER_TAG,
)


@pytest.fixture(autouse=True)
def clean_config():
    saved = config.GLOBAL_CONFIG.copy()
    yield
    config.GLOBAL_CONFIG = saved


class _FakeIterationRecord:
    def __init__(self, iteration, train_accuracy, kept=True):
        self.iteration = iteration
        self.train_accuracy = train_accuracy
        self.eval_accuracy = None
        self.train_cost = 0.0
        self.supervisor_cost = 0.0
        self.kept = kept
        self.reasoning = ''
        self.config_overrides = []


class _FakeReport:
    def __init__(self):
        self.iterations = [_FakeIterationRecord(0, 0.50), _FakeIterationRecord(1, 0.70)]
        self.best_iteration = 1
        self.best_train_accuracy = 0.70
        self.final_eval_accuracy = None
        self.total_supervisor_cost = 0.0
        self.best_code = ''
        self.best_config_overrides = []
        self.config_snapshot_path = 'config.yaml'


def test_init_creates_timestamped_dir(tmp_path):
    """Fresh init should mint a {TS}.orch_learner dir via savefile."""
    learner = OrchestrationLearner(
        interface_name='calculate_medical_value',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
        n_train=5,
        n_eval=5,
        max_iterations=1,
    )
    assert learner.out_dir.parent == tmp_path
    assert learner.out_dir.name.endswith(f'.{LEARNER_TAG}')
    # savefile auto-writes a config.yaml snapshot.
    assert (learner.out_dir / 'config.yaml').exists()
    # created_files keys include implementation.yaml
    assert 'implementation.yaml' in learner.created_files
    assert 'ptools_evolved.py' in learner.created_files


def test_init_file_under_is_orch_learner(tmp_path):
    learner = OrchestrationLearner(
        interface_name='x',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    assert learner.file_under == LEARNER_TAG


def test_save_implementation_shape_no_ptools_cfg(tmp_path):
    """Without ptools.<entry> config, falls back to using entry_point as fn."""
    learner = OrchestrationLearner(
        interface_name='calculate_medical_value',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    learner._entry_point_name = 'calculate_medical_value'
    path = learner.save_implementation()
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert 'calculate_medical_value' in data
    entry = data['calculate_medical_value']
    assert entry['method'] == 'direct'
    assert entry['fn'] == '__learned__.calculate_medical_value'
    assert entry['learner'] == LEARNER_TAG


def test_save_implementation_uses_config_fn_name(tmp_path):
    """When the original config bound entry_point via `direct, fn=X.Y`,
    the learner should emit `fn: __learned__.Y` (not __learned__.<entry>).
    This matches the medcalc case where calculate_medical_value is an
    Interface stub and `workflow` is the actual implementation function."""
    config.configure(ptools=dict(
        calculate_medical_value=dict(method='direct', fn='ptools.workflow'),
    ))
    learner = OrchestrationLearner(
        interface_name='calculate_medical_value',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    learner._entry_point_name = 'calculate_medical_value'
    path = learner.save_implementation()
    data = yaml.safe_load(path.read_text())
    assert data['calculate_medical_value']['fn'] == '__learned__.workflow'


def test_save_implementation_non_direct_method_ignored(tmp_path):
    """If the original config was `simulate` (not `direct`), don't try to
    extract a fn name from the config — the learned implementation is
    always a direct-style call to the learned function."""
    config.configure(ptools=dict(
        my_entry=dict(method='simulate'),
    ))
    learner = OrchestrationLearner(
        interface_name='my_entry',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    learner._entry_point_name = 'my_entry'
    path = learner.save_implementation()
    data = yaml.safe_load(path.read_text())
    assert data['my_entry']['fn'] == '__learned__.my_entry'


def test_save_implementation_fallback_entry_point(tmp_path):
    """When _entry_point_name isn't set, fall back to config or interface_name."""
    config.configure(evaluate=dict(entry_point='my_custom_entry'))
    learner = OrchestrationLearner(
        interface_name='other_name',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    path = learner.save_implementation()
    data = yaml.safe_load(path.read_text())
    assert data['other_name']['fn'] == '__learned__.my_custom_entry'


def test_report_before_fit(tmp_path):
    learner = OrchestrationLearner(
        interface_name='x',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    assert 'has not been called' in learner.report()


def test_report_after_fit(tmp_path):
    learner = OrchestrationLearner(
        interface_name='x',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    learner.report_obj = _FakeReport()
    summary = learner.report()
    assert 'best train accuracy: 70.0%' in summary
    assert 'iterations: 2' in summary


def test_resume_reuses_existing_dir(tmp_path):
    """With resume=<existing_dir>, init should NOT create a new timestamp dir."""
    existing = tmp_path / '20260101.120000.orch_learner'
    existing.mkdir()
    # Need a dummy report.json for resume path to be meaningful later, but
    # the init doesn't read it — only fit() does. For init-only test, an
    # empty dir suffices.

    learner = OrchestrationLearner(
        interface_name='calculate_medical_value',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
        resume=existing,
    )
    assert learner.out_dir == existing
    assert learner.resume == existing
    # created_files should point into the existing dir, not a new one.
    for name, path in learner.created_files.items():
        assert Path(path).parent == existing


def test_resume_missing_dir_raises(tmp_path):
    missing = tmp_path / 'does_not_exist'
    with pytest.raises(FileNotFoundError):
        OrchestrationLearner(
            interface_name='x',
            train_dir=str(tmp_path),
            config_file='conf/x.yaml',
            resume=missing,
        )


def test_learn_calls_fit_and_save(tmp_path, monkeypatch):
    """learn() should call fit() then save_implementation() — skipping distillation."""
    called = {'fit': 0, 'save': 0}

    def fake_fit(self):
        self.report_obj = _FakeReport()
        self._entry_point_name = 'calculate_medical_value'
        called['fit'] += 1
        return self

    orig_save = OrchestrationLearner.save_implementation

    def fake_save(self):
        called['save'] += 1
        return orig_save(self)

    monkeypatch.setattr(OrchestrationLearner, 'fit', fake_fit)
    monkeypatch.setattr(OrchestrationLearner, 'save_implementation', fake_save)

    learner = OrchestrationLearner(
        interface_name='calculate_medical_value',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    learner.learn()
    assert called['fit'] == 1
    assert called['save'] == 1
    # After learn(), implementation.yaml should exist on disk.
    assert (learner.out_dir / 'implementation.yaml').exists()


def test_implementation_yaml_resolvable_via_direct_factory(tmp_path):
    """End-to-end: write ptools_evolved.py + implementation.yaml, then
    check that the direct factory with fn=__learned__.<attr> resolves."""
    from secretagent.core import interface

    # Write a fake ptools_evolved.py into the Learner's out_dir.
    learner = OrchestrationLearner(
        interface_name='my_entry',
        train_dir=str(tmp_path),
        config_file='conf/x.yaml',
    )
    learner._entry_point_name = 'my_entry'
    (learner.out_dir / 'ptools_evolved.py').write_text(
        'def my_entry(x: str) -> str:\n'
        '    return f"learned:{x}"\n'
    )
    impl_path = learner.save_implementation()

    # Now exercise the direct factory.
    config.configure(learn=dict(train_dir=str(tmp_path)))

    def stub(x: str) -> str: ...
    stub.__name__ = 'my_entry'
    stub.__qualname__ = 'my_entry'
    iface = interface(stub)

    impl_yaml = yaml.safe_load(impl_path.read_text())
    entry_cfg = dict(impl_yaml['my_entry'])
    method = entry_cfg.pop('method')
    iface.implement_via(method, **entry_cfg)
    assert iface('world') == 'learned:world'
