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
        record.record(func="foo", args=(1,))
        assert len(rec) == 1
    assert record.RECORD == []


def test_recorder_clears_previous_records():
    record.RECORD = [{"func": "stale"}]
    with record.recorder() as rec:
        assert rec == []


# --- record() ---

def test_record_appends_when_recording():
    with record.recorder() as rec:
        record.record(func="translate", args=("hello",), output="hola")
        assert len(rec) == 1
        assert rec[0] == {"func": "translate", "args": ("hello",), "output": "hola"}


def test_record_ignores_when_not_recording():
    record.record(func="translate", args=("hello",))
    assert record.RECORD == []


def test_record_multiple_entries():
    with record.recorder() as rec:
        record.record(func="a", args=(1,))
        record.record(func="b", args=(2,))
        record.record(func="c", args=(3,))
        assert len(rec) == 3
        assert [r["func"] for r in rec] == ["a", "b", "c"]


def test_record_preserves_arbitrary_kwargs():
    with record.recorder() as rec:
        record.record(x=1, y="two", z=[3])
        assert rec[0] == {"x": 1, "y": "two", "z": [3]}


def test_yielded_list_is_same_object_as_global():
    with record.recorder() as rec:
        assert rec is record.RECORD


# --- thread safety ---

def test_concurrent_recording():
    """Two threads record independently without interference."""
    import threading

    results = {}

    def worker(name, entries):
        with record.recorder() as rec:
            for e in entries:
                record.record(func=name, val=e)
            results[name] = list(rec)

    t1 = threading.Thread(target=worker, args=('t1', [1, 2, 3]))
    t2 = threading.Thread(target=worker, args=('t2', [10, 20]))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results['t1']) == 3
    assert all(r['func'] == 't1' for r in results['t1'])
    assert len(results['t2']) == 2
    assert all(r['func'] == 't2' for r in results['t2'])
