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
    paths = savefile.filename_list(str(result_dir), ['a.csv', 'b.jsonl'])
    assert len(paths) == 2
    # directory was created
    assert paths[0].parent.exists()
    assert paths[0].parent == paths[1].parent
    # config.yaml was saved
    assert (paths[0].parent / 'config.yaml').exists()


def test_filename_list_with_file_under(result_dir):
    paths = savefile.filename_list(
        str(result_dir), ['results.csv'],
        file_under='test_expt')
    # directory name should contain the expt_name tag
    assert 'test_expt' in paths[0].parent.name


def test_filename_list_without_file_under(result_dir):
    paths = savefile.filename_list(str(result_dir), ['results.csv'])
    # directory name should contain the default _untagged_ tag
    dirname = paths[0].parent.name
    # timestamp format is YYYYMMDD.HHMMSS._untagged_ — two dots
    assert dirname.count('.') == 2
    assert savefile.DEFAULT_TAG in dirname


def test_filename_list_names_match(result_dir):
    names = ['results.csv', 'results.jsonl', 'extra.txt']
    paths = savefile.filename_list(str(result_dir), names)
    assert [p.name for p in paths] == names


def test_filename_list_config_yaml_contents(result_dir):
    config.configure(llm={'model': 'test-model'})
    paths = savefile.filename_list(str(result_dir), ['a.csv'])
    saved_cfg = OmegaConf.load(paths[0].parent / 'config.yaml')
    assert OmegaConf.select(saved_cfg, 'llm.model') == 'test-model'


# --- filename tests ---

def test_filename_returns_single_path(result_dir):
    path = savefile.filename(str(result_dir), 'results.csv')
    assert isinstance(path, Path)
    assert path.name == 'results.csv'
    assert path.parent.exists()


def test_filename_with_file_under(result_dir):
    path = savefile.filename(
        str(result_dir), 'results.csv',
        file_under='test_expt')
    assert 'test_expt' in path.parent.name


# --- filter_paths tests ---

def _make_expt_dir(base, name, cfg_dict):
    """Helper to create a fake experiment directory with config.yaml."""
    d = base / name
    d.mkdir()
    with open(d / 'config.yaml', 'w') as f:
        f.write(OmegaConf.to_yaml(OmegaConf.create(cfg_dict)))
    return d


def _all_subdirs(base):
    """Return all subdirectory Paths under base."""
    return sorted(base.iterdir())


def test_filter_paths_finds_all(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.exptA', {'llm': {'model': 'a'}})
    _make_expt_dir(result_dir, '20260102.120000.exptB', {'llm': {'model': 'b'}})
    dirs = savefile.filter_paths(_all_subdirs(result_dir), latest=0)
    assert len(dirs) == 2


def test_filter_paths_latest_per_tag(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.exptA', {'llm': {'model': 'a'}})
    _make_expt_dir(result_dir, '20260102.120000.exptA', {'llm': {'model': 'b'}})
    _make_expt_dir(result_dir, '20260103.120000.exptB', {'llm': {'model': 'c'}})
    dirs = savefile.filter_paths(_all_subdirs(result_dir), latest=1)
    assert len(dirs) == 2  # one per tag
    names = {d.name for d in dirs}
    assert '20260102.120000.exptA' in names  # most recent exptA
    assert '20260103.120000.exptB' in names


def test_filter_paths_config_filter(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.exptA', {'llm': {'model': 'model-a'}})
    _make_expt_dir(result_dir, '20260102.120000.exptB', {'llm': {'model': 'model-b'}})
    dirs = savefile.filter_paths(_all_subdirs(result_dir), dotlist=['llm.model=model-a'])
    assert len(dirs) == 1
    assert 'exptA' in dirs[0].name


def test_filter_paths_config_filter_no_match(result_dir):
    _make_expt_dir(result_dir, '20260101.120000.exptA', {'llm': {'model': 'model-a'}})
    dirs = savefile.filter_paths(_all_subdirs(result_dir), dotlist=['llm.model=no-such-model'])
    assert len(dirs) == 0


def test_filter_paths_combined_filters(result_dir):
    d1 = _make_expt_dir(result_dir, '20260101.120000.test_expt', {'llm': {'model': 'model-a'}})
    d2 = _make_expt_dir(result_dir, '20260102.120000.test_expt', {'llm': {'model': 'model-b'}})
    d3 = _make_expt_dir(result_dir, '20260103.120000.other', {'llm': {'model': 'model-a'}})
    dirs = savefile.filter_paths(
        [d1, d2, d3],
        dotlist=['llm.model=model-a'])
    assert len(dirs) == 2  # d1 and d3 match
    dirs = savefile.filter_paths(
        [d1, d2, d3],
        latest=1,
        dotlist=['llm.model=model-a'])
    assert len(dirs) == 2  # one per tag: test_expt and other


def test_filter_paths_empty_list(result_dir):
    dirs = savefile.filter_paths([])
    assert dirs == []


def test_filter_paths_skips_non_dirs(result_dir):
    (result_dir / 'stray_file.txt').write_text('hello')
    with pytest.warns(UserWarning, match='No config.yaml'):
        dirs = savefile.filter_paths(_all_subdirs(result_dir))
    assert dirs == []


def test_filter_paths_skips_dirs_without_config(result_dir):
    (result_dir / 'no_config_dir').mkdir()
    with pytest.warns(UserWarning, match='No config.yaml'):
        dirs = savefile.filter_paths(_all_subdirs(result_dir))
    assert dirs == []


def test_filter_paths_sorted_by_tag_then_newest(result_dir):
    _make_expt_dir(result_dir, '20260103.120000.c', {'x': 1})
    _make_expt_dir(result_dir, '20260101.120000.a', {'x': 1})
    _make_expt_dir(result_dir, '20260102.120000.b', {'x': 1})
    dirs = savefile.filter_paths(_all_subdirs(result_dir), latest=0)
    names = [d.name for d in dirs]
    # grouped by tag alphabetically, newest first within each tag
    assert names == ['20260101.120000.a', '20260102.120000.b', '20260103.120000.c']
