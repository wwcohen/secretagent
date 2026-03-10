"""Tests for secretagent.dataset."""

from secretagent.dataset import Case, Dataset


def _make_cases(n):
    return [Case(name=f'case_{i}', input_args=[i], expected_output=i * 2) for i in range(n)]


def _make_dataset(n=5):
    return Dataset(name='test', cases=_make_cases(n))


# --- Case ---

def test_case_minimal():
    c = Case(name='c1')
    assert c.name == 'c1'
    assert c.input_args is None
    assert c.expected_output is None


def test_case_with_fields():
    c = Case(name='c1', input_args=[1, 2], input_kw={'x': 3}, expected_output=6,
             metadata={'source': 'test'})
    assert c.input_args == [1, 2]
    assert c.input_kw == {'x': 3}
    assert c.expected_output == 6
    assert c.metadata == {'source': 'test'}


# --- Dataset ---

def test_dataset_summary():
    ds = _make_dataset(3)
    assert 'test' in ds.summary()
    assert '3' in ds.summary()


def test_dataset_head():
    ds = _make_dataset(5)
    result = ds.head(2)
    assert len(ds.cases) == 2
    assert ds.cases[0].name == 'case_0'
    assert result is ds


def test_dataset_tail():
    ds = _make_dataset(5)
    result = ds.tail(3)
    assert len(ds.cases) == 2
    assert ds.cases[0].name == 'case_3'
    assert result is ds


def test_dataset_shuffle_with_seed():
    ds = _make_dataset(10)
    original_names = [c.name for c in ds.cases]
    ds.shuffle(seed=42)
    shuffled_names = [c.name for c in ds.cases]
    assert len(shuffled_names) == 10
    assert set(shuffled_names) == set(original_names)
    assert shuffled_names != original_names  # very unlikely to be identical


def test_dataset_shuffle_deterministic():
    ds1 = _make_dataset(10)
    ds2 = _make_dataset(10)
    ds1.shuffle(seed=99)
    ds2.shuffle(seed=99)
    assert [c.name for c in ds1.cases] == [c.name for c in ds2.cases]


def test_dataset_shuffle_none_seed_is_noop():
    ds = _make_dataset(5)
    original_names = [c.name for c in ds.cases]
    ds.shuffle(seed=None)
    assert [c.name for c in ds.cases] == original_names


def test_dataset_chaining():
    ds = _make_dataset(10)
    ds.shuffle(seed=42).head(3)
    assert len(ds.cases) == 3
