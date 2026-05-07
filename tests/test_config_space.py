import pytest
from secretagent.optimize.config_space import ConfigSpace


# --- _expand_hierarchy ---

def test_expand_hierarchy_flat_key():
    cs = ConfigSpace()
    assert cs._expand_hierarchy('model', 'gpt5') == {'model': 'gpt5'}


def test_expand_hierarchy_dotted_key():
    cs = ConfigSpace()
    assert cs._expand_hierarchy('llm.model', 'gpt5') == {'llm': {'model': 'gpt5'}}


def test_expand_hierarchy_triple_dotted_key():
    cs = ConfigSpace()
    assert cs._expand_hierarchy('a.b.c', 42) == {'a': {'b': {'c': 42}}}


# --- _deep_merge ---

def test_deep_merge_disjoint():
    cs = ConfigSpace()
    base = {'a': 1}
    cs._deep_merge(base, {'b': 2})
    assert base == {'a': 1, 'b': 2}


def test_deep_merge_nested():
    cs = ConfigSpace()
    base = {'llm': {'model': 'big'}}
    cs._deep_merge(base, {'llm': {'thinking': True}})
    assert base == {'llm': {'model': 'big', 'thinking': True}}


def test_deep_merge_override():
    cs = ConfigSpace()
    base = {'llm': {'model': 'big'}}
    cs._deep_merge(base, {'llm': {'model': 'small'}})
    assert base == {'llm': {'model': 'small'}}


# --- __iter__ ---

def test_empty_variants():
    cs = ConfigSpace(variants={})
    results = list(cs)
    assert results == [{}]


def test_single_variant():
    cs = ConfigSpace(variants={'model': ['a', 'b']})
    results = list(cs)
    assert results == [{'model': 'a'}, {'model': 'b'}]


def test_cartesian_product():
    cs = ConfigSpace(variants={'x': [1, 2], 'y': ['a', 'b']})
    results = list(cs)
    assert len(results) == 4
    assert {'x': 1, 'y': 'a'} in results
    assert {'x': 1, 'y': 'b'} in results
    assert {'x': 2, 'y': 'a'} in results
    assert {'x': 2, 'y': 'b'} in results


def test_dotted_variants_deep_merged():
    """Two dotted keys sharing a prefix should be deep-merged, not overwritten."""
    cs = ConfigSpace(variants={
        'llm.model': ['big'],
        'llm.thinking': [True],
    })
    results = list(cs)
    assert results == [{'llm': {'model': 'big', 'thinking': True}}]


def test_dict_values_in_variants():
    cs = ConfigSpace(variants={
        'ptool.extract': [{'method': 'direct', 'fn': 'f1'}],
    })
    results = list(cs)
    assert results == [{'ptool': {'extract': {'method': 'direct', 'fn': 'f1'}}}]


# --- save / load round-trip ---

def test_save_load_roundtrip(tmp_path):
    path = str(tmp_path / 'space.yaml')
    cs = ConfigSpace(variants={
        'llm.model': ['big', 'small'],
        'name': ['fred'],
    })
    cs.save(path)
    loaded = ConfigSpace.load(path)
    assert loaded.variants == cs.variants
    assert list(loaded) == list(cs)
