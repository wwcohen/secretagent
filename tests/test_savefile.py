import os
import pytest
from pathlib import Path

from omegaconf import OmegaConf

from secretagent import config, savefile


@pytest.fixture(autouse=True)
def clean_config():
    """Reset config before and after each test."""
    saved = config.GLOBAL_CONFIG.copy()
    yield
    config.GLOBAL_CONFIG = saved


@pytest.fixture
def result_dir(tmp_path):
    """Configure evaluate.result_dir to a temp directory."""
    config.configure(evaluate={'result_dir': str(tmp_path), 'expt_name': 'test_expt'})
    return tmp_path


# --- filename_list tests ---

def test_filename_list_creates_directory(result_dir):
    paths = savefile.filename_list('evaluate.result_dir', ['a.csv', 'b.jsonl'])
    assert len(paths) == 2
    # directory was created
    assert paths[0].parent.exists()
    assert paths[0].parent == paths[1].parent
    # config.yaml was saved
    assert (paths[0].parent / 'config.yaml').exists()


def test_filename_list_with_file_under(result_dir):
    paths = savefile.filename_list(
        'evaluate.result_dir', ['results.csv'],
        file_under='evaluate.expt_name')
    # directory name should contain the expt_name tag
    assert 'test_expt' in paths[0].parent.name


def test_filename_list_without_file_under(result_dir):
    paths = savefile.filename_list('evaluate.result_dir', ['results.csv'])
    # directory name should be just a timestamp (no dot-separated tag)
    dirname = paths[0].parent.name
    # timestamp format is YYYYMMDD.HHMMSS — exactly one dot
    assert dirname.count('.') == 1


def test_filename_list_names_match(result_dir):
    names = ['results.csv', 'results.jsonl', 'extra.txt']
    paths = savefile.filename_list('evaluate.result_dir', names)
    assert [p.name for p in paths] == names


def test_filename_list_missing_basedir():
    config.configure(evaluate={})
    with pytest.raises(ValueError, match='required key'):
        savefile.filename_list('evaluate.result_dir', ['a.csv'])


def test_filename_list_config_yaml_contents(result_dir):
    config.configure(llm={'model': 'test-model'})
    paths = savefile.filename_list('evaluate.result_dir', ['a.csv'])
    saved_cfg = OmegaConf.load(paths[0].parent / 'config.yaml')
    assert OmegaConf.select(saved_cfg, 'llm.model') == 'test-model'


# --- filename tests ---

def test_filename_returns_single_path(result_dir):
    path = savefile.filename('evaluate.result_dir', 'results.csv')
    assert isinstance(path, Path)
    assert path.name == 'results.csv'
    assert path.parent.exists()


def test_filename_with_file_under(result_dir):
    path = savefile.filename(
        'evaluate.result_dir', 'results.csv',
        file_under='evaluate.expt_name')
    assert 'test_expt' in path.parent.name


# --- getfiles tests ---

def _make_expt_dir(base, name, cfg_dict):
    """Helper to create a fake experiment directory with config.yaml."""
    d = base / name
    d.mkdir()
    with open(d / 'config.yaml', 'w') as f:
        f.write(OmegaConf.to_yaml(OmegaConf.create(cfg_dict)))
    return d


def test_getfiles_finds_all(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.exptA', {'llm': {'model': 'a'}})
    _make_expt_dir(result_dir, '20260102.120000.exptB', {'llm': {'model': 'b'}})
    dirs = savefile.getfiles('evaluate.result_dir')
    assert len(dirs) == 2


def test_getfiles_filters_by_file_under(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.test_expt', {'llm': {'model': 'a'}})
    _make_expt_dir(result_dir, '20260102.120000.other', {'llm': {'model': 'b'}})
    dirs = savefile.getfiles('evaluate.result_dir', file_under='evaluate.expt_name')
    assert len(dirs) == 1
    assert 'test_expt' in dirs[0].name


def test_getfiles_most_recent(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.exptA', {'llm': {'model': 'a'}})
    _make_expt_dir(result_dir, '20260102.120000.exptB', {'llm': {'model': 'b'}})
    dirs = savefile.getfiles('evaluate.result_dir', most_recent=True)
    assert len(dirs) == 1
    assert 'exptB' in dirs[0].name


def test_getfiles_config_filter(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.exptA', {'llm': {'model': 'model-a'}})
    _make_expt_dir(result_dir, '20260102.120000.exptB', {'llm': {'model': 'model-b'}})
    dirs = savefile.getfiles('evaluate.result_dir', llm__model='model-a')
    assert len(dirs) == 1
    assert 'exptA' in dirs[0].name


def test_getfiles_config_filter_no_match(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.exptA', {'llm': {'model': 'model-a'}})
    dirs = savefile.getfiles('evaluate.result_dir', llm__model='no-such-model')
    assert len(dirs) == 0


def test_getfiles_combined_filters(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.test_expt', {'llm': {'model': 'model-a'}})
    _make_expt_dir(result_dir, '20260102.120000.test_expt', {'llm': {'model': 'model-b'}})
    _make_expt_dir(result_dir, '20260103.120000.other', {'llm': {'model': 'model-a'}})
    dirs = savefile.getfiles(
        'evaluate.result_dir',
        file_under='evaluate.expt_name',
        llm__model='model-a')
    assert len(dirs) == 1
    assert 'test_expt' in dirs[0].name


def test_getfiles_empty_dir(result_dir):
    dirs = savefile.getfiles('evaluate.result_dir')
    assert dirs == []


def test_getfiles_ignores_non_dirs(result_dir):
    # file without config.yaml should be ignored
    (result_dir / 'stray_file.txt').write_text('hello')
    dirs = savefile.getfiles('evaluate.result_dir')
    assert dirs == []


def test_getfiles_ignores_dirs_without_config(result_dir):
    (result_dir / 'no_config_dir').mkdir()
    dirs = savefile.getfiles('evaluate.result_dir')
    assert dirs == []


def test_getfiles_nonexistent_basedir(tmp_path):
    config.configure(evaluate={'result_dir': str(tmp_path / 'does_not_exist')})
    dirs = savefile.getfiles('evaluate.result_dir')
    assert dirs == []


def test_getfiles_sorted_oldest_first(result_dir):
    _make_expt_dir(result_dir, '20260103.120000.c', {'x': 1})
    _make_expt_dir(result_dir, '20260101.120000.a', {'x': 1})
    _make_expt_dir(result_dir, '20260102.120000.b', {'x': 1})
    dirs = savefile.getfiles('evaluate.result_dir')
    names = [d.name for d in dirs]
    assert names == sorted(names)
