"""Tests for the config encoder/decoder."""

import pytest
from secretagent.optimize.encoder import (
    SearchDimension, encode, decode, decode_dict, space_size, dim_sizes,
)


@pytest.fixture
def two_dims():
    return [
        SearchDimension(key="llm.model", values=["cheap", "mid", "expensive"]),
        SearchDimension(key="ptools.foo.method", values=["simulate", "direct"]),
    ]


class TestSearchDimension:
    def test_size(self):
        d = SearchDimension(key="x", values=[1, 2, 3])
        assert d.size == 3

    def test_empty(self):
        d = SearchDimension(key="x", values=[])
        assert d.size == 0


class TestEncode:
    def test_basic(self, two_dims):
        vec = encode(two_dims, {"llm.model": "mid", "ptools.foo.method": "direct"})
        assert vec == [1, 1]

    def test_first_values(self, two_dims):
        vec = encode(two_dims, {"llm.model": "cheap", "ptools.foo.method": "simulate"})
        assert vec == [0, 0]

    def test_last_values(self, two_dims):
        vec = encode(two_dims, {"llm.model": "expensive", "ptools.foo.method": "direct"})
        assert vec == [2, 1]

    def test_missing_key(self, two_dims):
        with pytest.raises(KeyError):
            encode(two_dims, {"llm.model": "cheap"})

    def test_invalid_value(self, two_dims):
        with pytest.raises(ValueError, match="not in"):
            encode(two_dims, {"llm.model": "nonexistent", "ptools.foo.method": "simulate"})


class TestDecode:
    def test_basic(self, two_dims):
        result = decode(two_dims, [1, 0])
        assert result == ["llm.model=mid", "ptools.foo.method=simulate"]

    def test_all_zeros(self, two_dims):
        result = decode(two_dims, [0, 0])
        assert result == ["llm.model=cheap", "ptools.foo.method=simulate"]

    def test_out_of_bounds_high(self, two_dims):
        with pytest.raises(IndexError, match="out of range"):
            decode(two_dims, [3, 0])

    def test_out_of_bounds_negative(self, two_dims):
        with pytest.raises(IndexError, match="out of range"):
            decode(two_dims, [-1, 0])

    def test_wrong_length(self, two_dims):
        with pytest.raises(ValueError, match="Vector length"):
            decode(two_dims, [0])


class TestDecodeDict:
    def test_basic(self, two_dims):
        result = decode_dict(two_dims, [2, 1])
        assert result == {"llm.model": "expensive", "ptools.foo.method": "direct"}

    def test_out_of_bounds(self, two_dims):
        with pytest.raises(IndexError):
            decode_dict(two_dims, [0, 5])


class TestRoundTrip:
    def test_encode_decode_roundtrip(self, two_dims):
        original = {"llm.model": "mid", "ptools.foo.method": "direct"}
        vec = encode(two_dims, original)
        recovered = decode_dict(two_dims, vec)
        assert recovered == original

    def test_all_configs(self, two_dims):
        """Every valid vector encodes and decodes back to itself."""
        for i in range(two_dims[0].size):
            for j in range(two_dims[1].size):
                vec = [i, j]
                d = decode_dict(two_dims, vec)
                assert encode(two_dims, d) == vec


class TestSpaceSize:
    def test_basic(self, two_dims):
        assert space_size(two_dims) == 6  # 3 * 2

    def test_single_dim(self):
        dims = [SearchDimension(key="x", values=[1, 2, 3, 4])]
        assert space_size(dims) == 4

    def test_empty(self):
        assert space_size([]) == 0


class TestDimSizes:
    def test_basic(self, two_dims):
        assert dim_sizes(two_dims) == [3, 2]
