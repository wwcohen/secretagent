"""Tests for the pipeline profiler."""

import json
from pathlib import Path

import pytest
import yaml

from secretagent.orchestrate.profiler import (
    PipelineProfile, PtoolProfile, ErrorPattern,
    profile_from_results, compute_lift, _detect_error_patterns,
)


def _make_result_dir(tmp_path, records, name='test'):
    """Create a result directory with config.yaml + results.jsonl."""
    d = tmp_path / f'20260101.120000.{name}'
    d.mkdir()
    (d / 'config.yaml').write_text(yaml.dump({'evaluate': {'expt_name': name}}))
    with open(d / 'results.jsonl', 'w') as f:
        for rec in records:
            f.write(json.dumps(rec) + '\n')
    return d


def _record(correct, cost, latency, rollout=None):
    """Build a synthetic JSONL record."""
    rec = {
        'correct': correct,
        'cost': cost,
        'latency': latency,
        'predicted_output': 'x',
        'expected_output': 'x' if correct else 'y',
    }
    if rollout is not None:
        rec['rollout'] = rollout
    return rec


def _step(func, cost=0.01, latency=0.5, tokens_in=100, tokens_out=50, output='ok'):
    """Build a synthetic rollout step."""
    return {
        'func': func,
        'args': ['test_input'],
        'kw': {},
        'output': output,
        'stats': {
            'cost': cost,
            'latency': latency,
            'input_tokens': tokens_in,
            'output_tokens': tokens_out,
        },
    }


class TestProfileBasicAggregates:
    def test_basic_counts(self, tmp_path):
        records = [
            _record(True, 0.01, 1.0, [_step('a'), _step('b')]),
            _record(False, 0.02, 2.0, [_step('a'), _step('b')]),
            _record(True, 0.015, 1.5, [_step('a'), _step('b')]),
        ]
        d = _make_result_dir(tmp_path, records)
        profile = profile_from_results([d])

        assert profile.n_cases == 3
        assert profile.n_cases_with_rollout == 3
        assert profile.accuracy == pytest.approx(2 / 3)
        assert profile.total_cost == pytest.approx(0.045)
        assert profile.total_latency == pytest.approx(4.5)
        assert profile.avg_cost == pytest.approx(0.015)
        assert profile.avg_latency == pytest.approx(1.5)


class TestProfilePerPtoolStats:
    def test_per_ptool_calls(self, tmp_path):
        records = [
            _record(True, 0.03, 1.0, [_step('a', cost=0.02), _step('b', cost=0.01)]),
            _record(True, 0.03, 1.0, [_step('a', cost=0.02), _step('b', cost=0.01)]),
        ]
        d = _make_result_dir(tmp_path, records)
        profile = profile_from_results([d])

        assert 'a' in profile.ptool_profiles
        assert 'b' in profile.ptool_profiles
        pp_a = profile.ptool_profiles['a']
        assert pp_a.n_calls == 2
        assert pp_a.calls_per_case == pytest.approx(1.0)
        assert pp_a.avg_cost == pytest.approx(0.02)

    def test_per_ptool_latency_tokens(self, tmp_path):
        records = [
            _record(True, 0.02, 1.0, [
                _step('a', latency=0.3, tokens_in=200, tokens_out=100),
            ]),
            _record(True, 0.02, 1.0, [
                _step('a', latency=0.5, tokens_in=400, tokens_out=200),
            ]),
        ]
        d = _make_result_dir(tmp_path, records)
        profile = profile_from_results([d])
        pp = profile.ptool_profiles['a']
        assert pp.avg_latency == pytest.approx(0.4)
        assert pp.avg_tokens_in == pytest.approx(300)
        assert pp.avg_tokens_out == pytest.approx(150)


class TestProfileCostFractions:
    def test_cost_fractions_sum_to_one(self, tmp_path):
        records = [
            _record(True, 0.03, 1.0, [
                _step('a', cost=0.02),
                _step('b', cost=0.005),
                _step('c', cost=0.005),
            ]),
        ]
        d = _make_result_dir(tmp_path, records)
        profile = profile_from_results([d])
        total = sum(pp.cost_fraction for pp in profile.ptool_profiles.values())
        assert total == pytest.approx(1.0)

    def test_cost_fraction_values(self, tmp_path):
        records = [
            _record(True, 0.03, 1.0, [
                _step('expensive', cost=0.09),
                _step('cheap', cost=0.01),
            ]),
        ]
        d = _make_result_dir(tmp_path, records)
        profile = profile_from_results([d])
        assert profile.ptool_profiles['expensive'].cost_fraction == pytest.approx(0.9)
        assert profile.ptool_profiles['cheap'].cost_fraction == pytest.approx(0.1)


class TestProfileAccuracyCorrelation:
    def test_presence_in_correct_incorrect(self, tmp_path):
        records = [
            # Correct case: both a and b called
            _record(True, 0.02, 1.0, [_step('a'), _step('b')]),
            # Incorrect case: only b called
            _record(False, 0.01, 0.5, [_step('b')]),
        ]
        d = _make_result_dir(tmp_path, records)
        profile = profile_from_results([d])

        pp_a = profile.ptool_profiles['a']
        assert pp_a.presence_in_correct == pytest.approx(1.0)  # in 1/1 correct cases
        assert pp_a.presence_in_incorrect == pytest.approx(0.0)  # in 0/1 incorrect cases

        pp_b = profile.ptool_profiles['b']
        assert pp_b.presence_in_correct == pytest.approx(1.0)
        assert pp_b.presence_in_incorrect == pytest.approx(1.0)


class TestProfileWithoutRollout:
    def test_no_rollout_gives_empty_ptool_profiles(self, tmp_path):
        records = [
            _record(True, 0.01, 1.0),
            _record(False, 0.02, 2.0),
        ]
        d = _make_result_dir(tmp_path, records)
        profile = profile_from_results([d])

        assert profile.n_cases == 2
        assert profile.n_cases_with_rollout == 0
        assert profile.accuracy == pytest.approx(0.5)
        assert profile.ptool_profiles == {}


class TestProfileErrorDetection:
    def test_error_patterns_populated(self, tmp_path):
        records = [
            _record(False, 0.01, 1.0, [
                _step('a', output='**exception: ValueError: bad input'),
            ]),
            _record(False, 0.01, 1.0, [
                _step('a', output='**exception: ValueError: bad input again'),
            ]),
        ]
        d = _make_result_dir(tmp_path, records)
        profile = profile_from_results([d])

        pp_a = profile.ptool_profiles['a']
        assert len(pp_a.error_patterns) >= 1
        total_freq = sum(ep.frequency for ep in pp_a.error_patterns)
        assert total_freq == 2


class TestProfileEmptyResults:
    def test_empty_jsonl_no_crash(self, tmp_path):
        d = _make_result_dir(tmp_path, [], name='empty')
        profile = profile_from_results([d])
        assert profile.n_cases == 0
        assert profile.ptool_profiles == {}


class TestComputeLift:
    def test_lift_basic(self):
        p1 = PipelineProfile(accuracy=0.8, ptool_profiles={'a': PtoolProfile(name='a')})
        p2 = PipelineProfile(accuracy=0.6, ptool_profiles={'a': PtoolProfile(name='a')})
        assert compute_lift(p1, p2, 'a') == pytest.approx(0.2)

    def test_lift_missing_ptool(self):
        p1 = PipelineProfile(accuracy=0.8, ptool_profiles={})
        p2 = PipelineProfile(accuracy=0.6, ptool_profiles={'a': PtoolProfile(name='a')})
        assert compute_lift(p1, p2, 'a') is None


class TestDetectErrorPatterns:
    def test_groups_by_prefix(self):
        errors = [
            {'output': '**exception: TypeError: foo'},
            {'output': '**exception: TypeError: foo'},
            {'output': '**exception: ValueError: bar'},
        ]
        patterns = _detect_error_patterns(errors)
        assert len(patterns) == 2
        assert patterns[0].frequency == 2  # most frequent first
        assert len(patterns[0].example_cases) <= 3
