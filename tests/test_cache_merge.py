import pickle
import pytest
from dataclasses import dataclass

from typer.testing import CliRunner

from secretagent.cli.cache_merge import app


runner = CliRunner()


@dataclass
class FakeCacheEntry:
    value: object


def _write_cache(path, entries):
    with open(path, 'wb') as f:
        pickle.dump(entries, f)


def _read_cache(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


@pytest.fixture
def two_dirs(tmp_path):
    """Create two cache directories with overlapping and unique files."""
    dir1 = tmp_path / "cache1"
    dir2 = tmp_path / "cache2"
    dir1.mkdir()
    dir2.mkdir()

    # Shared file name with different entries
    _write_cache(dir1 / ".mod.llm_impl", {
        'key1': FakeCacheEntry(value="result1"),
        'key2': FakeCacheEntry(value="result2"),
    })
    _write_cache(dir2 / ".mod.llm_impl", {
        'key2': FakeCacheEntry(value="result2_updated"),
        'key3': FakeCacheEntry(value="result3"),
    })

    # File only in dir1
    _write_cache(dir1 / ".mod.agent", {
        'a1': FakeCacheEntry(value="agent1"),
    })

    # File only in dir2
    _write_cache(dir2 / ".mod.other", {
        'o1': FakeCacheEntry(value="other1"),
    })

    return dir1, dir2


def test_merge_to_output_dir(two_dirs, tmp_path):
    dir1, dir2 = two_dirs
    out = tmp_path / "merged"

    result = runner.invoke(app, [str(dir1), str(dir2), '-o', str(out)])
    assert result.exit_code == 0

    # Shared file: entries from both, dir2 wins on collision
    merged = _read_cache(out / ".mod.llm_impl")
    assert len(merged) == 3
    assert merged['key1'].value == "result1"
    assert merged['key2'].value == "result2_updated"
    assert merged['key3'].value == "result3"

    # File only in dir1
    agent = _read_cache(out / ".mod.agent")
    assert len(agent) == 1
    assert agent['a1'].value == "agent1"

    # File only in dir2
    other = _read_cache(out / ".mod.other")
    assert len(other) == 1


def test_merge_in_place(two_dirs):
    dir1, dir2 = two_dirs

    result = runner.invoke(app, [str(dir1), str(dir2)])
    assert result.exit_code == 0

    # dir1 should now contain merged results
    merged = _read_cache(dir1 / ".mod.llm_impl")
    assert len(merged) == 3

    # dir1 should also have the file only from dir2
    other = _read_cache(dir1 / ".mod.other")
    assert len(other) == 1


def test_merge_nonexistent_dir(tmp_path):
    dir1 = tmp_path / "cache1"
    dir1.mkdir()
    _write_cache(dir1 / ".mod.x", {'k': FakeCacheEntry(value="v")})

    result = runner.invoke(app, [str(dir1), str(tmp_path / "nope")])
    assert result.exit_code == 1
    assert "not a directory" in result.output


def test_merge_empty_dirs(tmp_path):
    dir1 = tmp_path / "empty1"
    dir2 = tmp_path / "empty2"
    dir1.mkdir()
    dir2.mkdir()

    result = runner.invoke(app, [str(dir1), str(dir2)])
    assert result.exit_code == 1
    assert "No cache files found" in result.output


def test_merge_skips_corrupt_file(tmp_path):
    dir1 = tmp_path / "cache1"
    dir2 = tmp_path / "cache2"
    dir1.mkdir()
    dir2.mkdir()

    # Corrupt file in dir1
    (dir1 / ".mod.bad").write_text("not a pickle")
    # Valid file in dir2 with same name
    _write_cache(dir2 / ".mod.bad", {
        'k': FakeCacheEntry(value="good"),
    })

    out = tmp_path / "out"
    result = runner.invoke(app, [str(dir1), str(dir2), '-o', str(out)])
    assert result.exit_code == 0
    assert "Warning" in result.output

    merged = _read_cache(out / ".mod.bad")
    assert merged['k'].value == "good"
