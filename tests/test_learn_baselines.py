import importlib.util
import json

import pytest
from omegaconf import OmegaConf

from secretagent import config
from secretagent.learn.baselines import RoteLearner


@pytest.fixture(autouse=True)
def clean_config():
    """Reset config before and after each test."""
    saved = config.GLOBAL_CONFIG.copy()
    yield
    config.GLOBAL_CONFIG = saved


def _make_recording_dir(base, name, records):
    """Create a fake recording directory with config.yaml and results.jsonl."""
    d = base / name
    d.mkdir()
    with open(d / 'config.yaml', 'w') as f:
        f.write(OmegaConf.to_yaml(OmegaConf.create({'llm': {'model': 'test'}})))
    with open(d / 'results.jsonl', 'w') as f:
        for rec in records:
            f.write(json.dumps(rec) + '\n')
    return d


def _make_records(interface_name, cases_data):
    """Build JSONL records from (args, kw, output) tuples, one rollout step each."""
    records = []
    for args, kw, output in cases_data:
        records.append({
            'predicted_output': output,
            'expected_output': output,
            'rollout': [
                {'func': interface_name, 'args': args, 'kw': kw or {}, 'output': output},
            ],
        })
    return records


def _make_learner(tmp_path, interface_name, cases_data):
    """Create a RoteLearner from synthetic data."""
    records = _make_records(interface_name, cases_data)
    _make_recording_dir(tmp_path, '20260101.120000.expt', records)
    learner = RoteLearner(
        interface_name=interface_name,
        train_dir=str(tmp_path / 'train'),
    )
    learner.collect_distillation_data([tmp_path / '20260101.120000.expt'])
    return learner


def _load_learned(path):
    """Import the generated learned.py module."""
    spec = importlib.util.spec_from_file_location('learned', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- fit() / save_implementation() tests ---


def test_save_implementation_creates_file(tmp_path):
    learner = _make_learner(tmp_path, 'my_func', [(['a'], None, 'x')])
    learner.fit()
    outpath = learner.save_implementation()
    assert outpath.exists()
    assert outpath.name == 'implementation.yaml'


def test_returns_most_common(tmp_path):
    learner = _make_learner(tmp_path, 'my_func', [
        (['hello'], None, 'world'),
        (['hello'], None, 'world'),
        (['hello'], None, 'earth'),
    ])
    learner.fit()
    mod = _load_learned(learner.save_implementation().parent / 'learned.py')
    assert mod.my_func('hello') == 'world'


def test_returns_none_for_unseen(tmp_path):
    learner = _make_learner(tmp_path, 'my_func', [(['a'], None, 'x')])
    learner.fit()
    mod = _load_learned(learner.save_implementation().parent / 'learned.py')
    assert mod.my_func('unseen') is None


def test_multiple_inputs(tmp_path):
    learner = _make_learner(tmp_path, 'f', [
        (['a'], None, '1'),
        (['b'], None, '2'),
    ])
    learner.fit()
    mod = _load_learned(learner.save_implementation().parent / 'learned.py')
    assert mod.f('a') == '1'
    assert mod.f('b') == '2'


def test_with_kwargs(tmp_path):
    learner = _make_learner(tmp_path, 'f', [
        ([], {'x': 1, 'y': 2}, 'ok'),
    ])
    learner.fit()
    mod = _load_learned(learner.save_implementation().parent / 'learned.py')
    assert mod.f(x=1, y=2) == 'ok'
    assert mod.f(x=1, y=99) is None


def test_with_mixed_args_and_kwargs(tmp_path):
    learner = _make_learner(tmp_path, 'f', [
        (['pos'], {'key': 'val'}, 'result'),
    ])
    learner.fit()
    mod = _load_learned(learner.save_implementation().parent / 'learned.py')
    assert mod.f('pos', key='val') == 'result'


def test_function_named_after_interface(tmp_path):
    learner = _make_learner(tmp_path, 'classify', [(['a'], None, 'x')])
    learner.fit()
    mod = _load_learned(learner.save_implementation().parent / 'learned.py')
    assert hasattr(mod, 'classify')
    assert mod.classify('a') == 'x'


def test_preserves_list_output(tmp_path):
    learner = _make_learner(tmp_path, 'f', [(['a'], None, ['x', 'y'])])
    learner.fit()
    mod = _load_learned(learner.save_implementation().parent / 'learned.py')
    assert mod.f('a') == ['x', 'y']


def test_preserves_dict_output(tmp_path):
    learner = _make_learner(tmp_path, 'f', [(['a'], None, {'k': 'v'})])
    learner.fit()
    mod = _load_learned(learner.save_implementation().parent / 'learned.py')
    assert mod.f('a') == {'k': 'v'}


# --- report() tests ---


def test_report_returns_string(tmp_path):
    learner = _make_learner(tmp_path, 'f', [
        (['a'], None, 'x'),
        (['a'], None, 'x'),
        (['b'], None, 'y'),
    ])
    learner.fit()
    result = learner.report()
    assert isinstance(result, str)
    assert 'inputs' in result
    assert 'coverage' in result


# --- out_dir tests ---


def test_out_dir_has_data_json(tmp_path):
    learner = _make_learner(tmp_path, 'f', [(['a'], None, 'x')])
    assert (learner.out_dir / 'data.json').exists()


def test_out_dir_has_sources_txt(tmp_path):
    learner = _make_learner(tmp_path, 'f', [(['a'], None, 'x')])
    sources = (learner.out_dir / 'sources.txt').read_text().strip().split('\n')
    assert len(sources) == 1
