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


# --- stratified_sample ---

def _make_grouped_dataset():
    """3 groups: A(6), B(3), C(1) = 10 cases."""
    cases = []
    for i in range(6):
        cases.append(Case(name=f'A_{i}', metadata={'group': 'A'}, input_args=[i]))
    for i in range(3):
        cases.append(Case(name=f'B_{i}', metadata={'group': 'B'}, input_args=[i]))
    cases.append(Case(name='C_0', metadata={'group': 'C'}, input_args=[0]))
    return Dataset(name='grouped', cases=cases)


def test_stratified_sample_total_count():
    ds = _make_grouped_dataset()
    sampled = ds.stratified_sample(5, key=lambda c: c.metadata['group'])
    assert len(sampled.cases) == 5


def test_stratified_sample_all_groups_represented():
    ds = _make_grouped_dataset()
    sampled = ds.stratified_sample(5, key=lambda c: c.metadata['group'])
    groups = {c.metadata['group'] for c in sampled.cases}
    assert groups == {'A', 'B', 'C'}


def test_stratified_sample_proportional():
    ds = _make_grouped_dataset()  # A=6, B=3, C=1
    sampled = ds.stratified_sample(5, key=lambda c: c.metadata['group'])
    counts = {}
    for c in sampled.cases:
        g = c.metadata['group']
        counts[g] = counts.get(g, 0) + 1
    # A should get the most, C at least 1
    assert counts['A'] >= counts['B'] >= counts['C']
    assert counts['C'] >= 1


def test_stratified_sample_n_larger_than_dataset():
    ds = _make_grouped_dataset()
    sampled = ds.stratified_sample(100, key=lambda c: c.metadata['group'])
    assert len(sampled.cases) == 10


def test_stratified_sample_deterministic():
    ds = _make_grouped_dataset()
    s1 = ds.stratified_sample(5, key=lambda c: c.metadata['group'], seed=42)
    s2 = ds.stratified_sample(5, key=lambda c: c.metadata['group'], seed=42)
    assert [c.name for c in s1.cases] == [c.name for c in s2.cases]
