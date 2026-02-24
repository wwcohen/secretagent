import pytest
from secretagent import record


@pytest.fixture(autouse=True)
def reset_recording_state():
    """Reset recording globals before each test."""
    record.RECORDING = False
    record.RECORD = []
    yield
    record.RECORDING = False
    record.RECORD = []


# --- recorder() context manager ---

def test_recorder_yields_empty_list():
    with record.recorder() as rec:
        assert rec == []


def test_recorder_enables_recording():
    assert record.RECORDING is False
    with record.recorder():
        assert record.RECORDING is True
    assert record.RECORDING is False


def test_recorder_clears_record_on_exit():
    with record.recorder() as rec:
        record._record(func="foo", args=(1,))
        assert len(rec) == 1
    assert record.RECORD == []


def test_recorder_clears_previous_records():
    record.RECORD = [{"func": "stale"}]
    with record.recorder() as rec:
        assert rec == []


# --- _record() ---

def test_record_appends_when_recording():
    with record.recorder() as rec:
        record._record(func="translate", args=("hello",), output="hola")
        assert len(rec) == 1
        assert rec[0] == {"func": "translate", "args": ("hello",), "output": "hola"}


def test_record_ignores_when_not_recording():
    record._record(func="translate", args=("hello",))
    assert record.RECORD == []


def test_record_multiple_entries():
    with record.recorder() as rec:
        record._record(func="a", args=(1,))
        record._record(func="b", args=(2,))
        record._record(func="c", args=(3,))
        assert len(rec) == 3
        assert [r["func"] for r in rec] == ["a", "b", "c"]


def test_record_preserves_arbitrary_kwargs():
    with record.recorder() as rec:
        record._record(x=1, y="two", z=[3])
        assert rec[0] == {"x": 1, "y": "two", "z": [3]}


def test_yielded_list_is_same_object_as_global():
    with record.recorder() as rec:
        assert rec is record.RECORD
