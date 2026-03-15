import pickle
import pytest
from dataclasses import dataclass

from secretagent.cache_util import extract_cached_stats, _is_stats_dict, _find_stats


@dataclass
class FakeCacheEntry:
    """Mimics cachier's CacheEntry dataclass."""
    value: object


def _make_stats(input_tokens=100, output_tokens=50, latency=1.0, cost=0.001):
    return dict(input_tokens=input_tokens, output_tokens=output_tokens,
                latency=latency, cost=cost)


def _write_cache_file(path, entries):
    """Write a dict of {key: FakeCacheEntry} as a pickle file."""
    with open(path, 'wb') as f:
        pickle.dump(entries, f)


# --- _is_stats_dict ---

def test_is_stats_dict_true():
    assert _is_stats_dict(_make_stats())


def test_is_stats_dict_missing_key():
    assert not _is_stats_dict({'input_tokens': 1, 'cost': 0.01})


def test_is_stats_dict_not_dict():
    assert not _is_stats_dict("not a dict")


# --- _find_stats ---

def test_find_stats_bare_dict():
    s = _make_stats()
    assert _find_stats(s) is s


def test_find_stats_in_tuple():
    s = _make_stats()
    assert _find_stats(("some output", s)) is s


def test_find_stats_triple_tuple():
    s = _make_stats()
    assert _find_stats(("answer", s, [{"thought": "hi"}])) is s


def test_find_stats_none_for_no_match():
    assert _find_stats(("just", "strings")) is None


# --- extract_cached_stats ---

@pytest.fixture
def cache_dir(tmp_path):
    """Create a fake cache directory with two cache files."""
    # llm_impl-style: (str, stats)
    s1 = _make_stats(input_tokens=100, cost=0.001)
    s2 = _make_stats(input_tokens=200, cost=0.002)
    _write_cache_file(tmp_path / '.mod.llm_impl', {
        'key1': FakeCacheEntry(value=("output1", s1)),
        'key2': FakeCacheEntry(value=("output2", s2)),
    })
    # run_agent-style: (answer, stats, messages)
    s3 = _make_stats(input_tokens=300, cost=0.003)
    _write_cache_file(tmp_path / '.mod.run_agent', {
        'key3': FakeCacheEntry(value=(42, s3, [{"thought": "ok"}])),
    })
    return tmp_path


def test_extract_finds_all_entries(cache_dir):
    stats = extract_cached_stats(str(cache_dir))
    assert len(stats) == 3


def test_extract_returns_correct_values(cache_dir):
    stats = extract_cached_stats(str(cache_dir))
    costs = sorted(s['cost'] for s in stats)
    assert costs == [0.001, 0.002, 0.003]


def test_extract_skips_incomplete_entries(tmp_path):
    _write_cache_file(tmp_path / '.cache', {
        'done': FakeCacheEntry(value=("out", _make_stats())),
        'pending': FakeCacheEntry(value=None),
    })
    stats = extract_cached_stats(str(tmp_path))
    assert len(stats) == 1


def test_extract_skips_non_pickle_files(tmp_path):
    (tmp_path / 'README.txt').write_text("not a pickle")
    _write_cache_file(tmp_path / '.cache', {
        'k': FakeCacheEntry(value=("out", _make_stats())),
    })
    stats = extract_cached_stats(str(tmp_path))
    assert len(stats) == 1


def test_extract_skips_dirs(tmp_path):
    (tmp_path / 'subdir').mkdir()
    _write_cache_file(tmp_path / '.cache', {
        'k': FakeCacheEntry(value=("out", _make_stats())),
    })
    stats = extract_cached_stats(str(tmp_path))
    assert len(stats) == 1


def test_extract_empty_dir(tmp_path):
    stats = extract_cached_stats(str(tmp_path))
    assert stats == []


def test_extract_no_cache_dir_raises():
    with pytest.raises(ValueError, match="No cache_dir"):
        extract_cached_stats(None)
