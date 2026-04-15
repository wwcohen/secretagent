"""Tests for the pipeline transforms system."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from secretagent.orchestrate.improve import (
    register_transform, get_transform, _TRANSFORMS,
    improve_pipeline, ImprovementReport,
)
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.profiler import PipelineProfile, PtoolProfile
from secretagent.orchestrate.pipeline import Pipeline
from secretagent.orchestrate.catalog import PtoolCatalog


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def simple_profile():
    return PipelineProfile(
        accuracy=0.7,
        total_cost=0.1,
        avg_cost=0.01,
        n_cases=10,
        n_cases_with_rollout=10,
        ptool_profiles={
            'a': PtoolProfile(
                name='a', n_calls=10, cost_fraction=0.6,
                presence_in_correct=0.9, presence_in_incorrect=0.5,
                lift=0.01,
            ),
            'b': PtoolProfile(
                name='b', n_calls=10, cost_fraction=0.4,
                presence_in_correct=0.8, presence_in_incorrect=0.3,
            ),
        },
    )


@pytest.fixture
def empty_catalog():
    return PtoolCatalog([])


# ── Registry tests ───────────────────────────────────────────────────

class TestTransformRegistry:
    def test_register_and_get(self):
        # Transforms are registered at import time via transforms/__init__.py
        assert get_transform('prune') is not None
        assert get_transform('downgrade') is not None

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match='unknown transform'):
            get_transform('nonexistent_transform_xyz')

    def test_all_six_registered(self):
        expected = {'prune', 'downgrade', 'induce', 'expand', 'repair', 'restructure'}
        assert expected <= set(_TRANSFORMS.keys())


# ── Base class helper tests ──────────────────────────────────────────

class TestGenerateCodeHelper:
    @patch('secretagent.llm_util.llm')
    @patch('secretagent.orchestrate.composer._ruff_fix')
    @patch('secretagent.orchestrate.composer._extract_code')
    def test_generate_code(self, mock_extract, mock_ruff, mock_llm):
        mock_llm.return_value = ('```python\nreturn 42\n```', {})
        mock_extract.return_value = 'return 42'
        mock_ruff.return_value = 'return 42'

        t = get_transform('induce')
        result = t._generate_code('test prompt', 'def f(x: str) -> int:')
        assert result == 'return 42'
        mock_llm.assert_called_once()


class TestValidateCode:
    def test_valid_code_returns_pipeline(self):
        t = get_transform('prune')
        p = t._validate_code('return 42', 'def f() -> int:', {})
        assert isinstance(p, Pipeline)
        assert p() == 42

    def test_invalid_code_raises(self):
        t = get_transform('prune')
        with pytest.raises(Exception):
            t._validate_code('def !!!invalid', 'def f():', {})


# ── Stub tests ───────────────────────────────────────────────────────

class TestStubsRaiseNotImplemented:
    """Transforms not yet implemented should raise NotImplementedError."""

    @pytest.mark.parametrize('name', ['induce', 'expand', 'restructure'])
    def test_propose_raises(self, name, simple_profile, empty_catalog):
        t = get_transform(name)
        with pytest.raises(NotImplementedError):
            t.propose(simple_profile, empty_catalog)

    @pytest.mark.parametrize('name', ['induce', 'expand', 'restructure'])
    def test_apply_raises(self, name, empty_catalog):
        t = get_transform(name)
        proposal = TransformProposal(transform_name=name, rationale='test')
        pipeline = Pipeline('return 1', 'def f() -> int:', {})
        with pytest.raises(NotImplementedError):
            t.apply(proposal, pipeline, empty_catalog)


# ── Implemented transform tests ─────────────────────────────────────

class TestDowngradeTransform:
    def test_propose_identifies_expensive_ptools(self):
        t = get_transform('downgrade')
        profile = PipelineProfile(ptool_profiles={
            'expensive': PtoolProfile(name='expensive', cost_fraction=0.6, avg_cost=0.05),
            'cheap': PtoolProfile(name='cheap', cost_fraction=0.4, avg_cost=0.01),
        })
        proposal = t.propose(profile, PtoolCatalog([]))
        assert proposal.transform_name == 'downgrade'
        assert len(proposal.changes) == 1
        assert proposal.changes[0]['ptool'] == 'expensive'

    def test_apply_returns_config_with_cheaper_model(self):
        from secretagent import config
        t = get_transform('downgrade')
        proposal = TransformProposal(
            transform_name='downgrade',
            rationale='test',
            changes=[{'ptool': 'expensive', 'cost_fraction': 0.6, 'avg_cost': 0.05}],
        )
        pipeline = Pipeline('return 1', 'def f() -> int:', {})
        with config.configuration(llm={'model': 'together_ai/deepseek-ai/DeepSeek-V3.1'}):
            result = t.apply(proposal, pipeline, PtoolCatalog([]))
        assert result.success is True
        assert result.new_config is not None
        assert 'ptools.expensive.model' in result.new_config

    def test_apply_fails_when_already_cheapest(self):
        from secretagent import config
        t = get_transform('downgrade')
        proposal = TransformProposal(
            transform_name='downgrade',
            rationale='test',
            changes=[{'ptool': 'x', 'cost_fraction': 0.6, 'avg_cost': 0.01}],
        )
        pipeline = Pipeline('return 1', 'def f() -> int:', {})
        with config.configuration(llm={'model': 'together_ai/google/gemma-3n-E4B-it'}):
            result = t.apply(proposal, pipeline, PtoolCatalog([]))
        assert result.success is False
        assert 'cheapest' in result.message


class TestPruneTransform:
    def test_propose_identifies_low_lift_ptools(self):
        t = get_transform('prune')
        profile = PipelineProfile(ptool_profiles={
            'useless': PtoolProfile(name='useless', lift=0.005, cost_fraction=0.3),
            'useful': PtoolProfile(name='useful', lift=0.15, cost_fraction=0.7),
        })
        proposal = t.propose(profile, PtoolCatalog([]))
        assert proposal.transform_name == 'prune'
        assert len(proposal.changes) == 1
        assert proposal.changes[0]['ptool'] == 'useless'

    @patch('secretagent.llm_util.llm')
    @patch('secretagent.orchestrate.composer._extract_code')
    @patch('secretagent.orchestrate.composer._ruff_fix')
    def test_apply_generates_new_pipeline(self, mock_ruff, mock_extract, mock_llm):
        mock_llm.return_value = ('```python\nreturn 42\n```', {})
        mock_extract.return_value = 'return 42'
        mock_ruff.return_value = 'return 42'

        t = get_transform('prune')
        proposal = TransformProposal(
            transform_name='prune',
            rationale='test',
            changes=[{'ptool': 'useless', 'lift': 0.005, 'cost_fraction': 0.3}],
        )
        pipeline = Pipeline('return 42', 'def f() -> int:', {})
        result = t.apply(proposal, pipeline, PtoolCatalog([]))
        assert result.success is True
        assert result.new_pipeline_code == 'return 42'


class TestRepairTransform:
    def test_propose_identifies_error_ptools(self):
        from secretagent.orchestrate.profiler import ErrorPattern
        t = get_transform('repair')
        profile = PipelineProfile(ptool_profiles={
            'buggy': PtoolProfile(
                name='buggy', n_calls=10,
                error_patterns=[
                    ErrorPattern(pattern='**exception: ValueError', frequency=5),
                ],
            ),
            'stable': PtoolProfile(name='stable', n_calls=10),
        })
        proposal = t.propose(profile, PtoolCatalog([]))
        assert proposal.transform_name == 'repair'
        assert len(proposal.changes) == 1
        assert proposal.changes[0]['ptool'] == 'buggy'
        assert proposal.changes[0]['total_errors'] == 5

    @patch('secretagent.llm_util.llm')
    @patch('secretagent.orchestrate.composer._extract_code')
    @patch('secretagent.orchestrate.composer._ruff_fix')
    def test_apply_generates_repaired_pipeline(self, mock_ruff, mock_extract, mock_llm):
        # Use simple single-statement code to avoid Pipeline._compile
        # indentation normalization issues with try/except blocks
        repaired = 'return buggy(x) if buggy(x) is not None else 0'
        mock_llm.return_value = (f'```python\n{repaired}\n```', {})
        mock_extract.return_value = repaired
        mock_ruff.return_value = repaired

        t = get_transform('repair')
        proposal = TransformProposal(
            transform_name='repair',
            rationale='test',
            changes=[{'ptool': 'buggy', 'total_errors': 5, 'error_rate': 0.5,
                       'top_patterns': ['**exception: ValueError']}],
        )
        pipeline = Pipeline('return buggy(x)', 'def f(x: str) -> int:', {'buggy': lambda x: 0})
        result = t.apply(proposal, pipeline, PtoolCatalog([]))
        assert result.success is True
        assert result.new_pipeline_code == repaired
        assert 'buggy' in result.message


# ── should_apply logic tests ────────────────────────────────────────

class TestShouldApplyLogic:
    def test_prune_triggers_on_low_lift(self):
        t = get_transform('prune')
        profile = PipelineProfile(ptool_profiles={
            'a': PtoolProfile(name='a', lift=0.01),
        })
        assert t.should_apply(profile) is True

    def test_prune_skips_when_no_lift_data(self):
        t = get_transform('prune')
        profile = PipelineProfile(ptool_profiles={
            'a': PtoolProfile(name='a', lift=None),
        })
        assert t.should_apply(profile) is False

    def test_prune_skips_when_lift_is_high(self):
        t = get_transform('prune')
        profile = PipelineProfile(ptool_profiles={
            'a': PtoolProfile(name='a', lift=0.15),
        })
        assert t.should_apply(profile) is False

    def test_downgrade_triggers_on_high_cost(self):
        t = get_transform('downgrade')
        profile = PipelineProfile(ptool_profiles={
            'a': PtoolProfile(name='a', cost_fraction=0.5),
        })
        assert t.should_apply(profile) is True

    def test_downgrade_skips_on_low_cost(self):
        t = get_transform('downgrade')
        profile = PipelineProfile(ptool_profiles={
            'a': PtoolProfile(name='a', cost_fraction=0.2),
        })
        assert t.should_apply(profile) is False

    def test_induce_always_applies(self):
        t = get_transform('induce')
        assert t.should_apply(PipelineProfile()) is True

    def test_expand_triggers_on_expensive_inaccurate(self):
        t = get_transform('expand')
        profile = PipelineProfile(
            accuracy=0.8,
            ptool_profiles={
                'a': PtoolProfile(name='a', cost_fraction=0.5, presence_in_correct=0.5),
            },
        )
        assert t.should_apply(profile) is True

    def test_expand_skips_accurate_ptool(self):
        t = get_transform('expand')
        profile = PipelineProfile(
            accuracy=0.8,
            ptool_profiles={
                'a': PtoolProfile(name='a', cost_fraction=0.5, presence_in_correct=0.9),
            },
        )
        assert t.should_apply(profile) is False

    def test_repair_triggers_on_errors(self):
        from secretagent.orchestrate.profiler import ErrorPattern
        t = get_transform('repair')
        profile = PipelineProfile(ptool_profiles={
            'a': PtoolProfile(
                name='a',
                error_patterns=[ErrorPattern(pattern='err', frequency=3)],
            ),
        })
        assert t.should_apply(profile) is True

    def test_repair_skips_no_errors(self):
        t = get_transform('repair')
        profile = PipelineProfile(ptool_profiles={
            'a': PtoolProfile(name='a'),
        })
        assert t.should_apply(profile) is False

    def test_restructure_always_applies(self):
        t = get_transform('restructure')
        assert t.should_apply(PipelineProfile()) is True


# ── Improvement loop test ────────────────────────────────────────────

class TestImprovePipeline:
    def test_with_stubs_produces_report(self, tmp_path):
        # Create a result dir
        d = tmp_path / '20260101.120000.test'
        d.mkdir()
        (d / 'config.yaml').write_text(yaml.dump({'evaluate': {'expt_name': 'test'}}))
        records = [
            {
                'correct': True, 'cost': 0.01, 'latency': 1.0,
                'rollout': [
                    {'func': 'a', 'args': ['x'], 'kw': {}, 'output': 'ok',
                     'stats': {'cost': 0.01, 'latency': 1.0, 'input_tokens': 100, 'output_tokens': 50}},
                ],
            },
        ]
        with open(d / 'results.jsonl', 'w') as f:
            for rec in records:
                f.write(json.dumps(rec) + '\n')

        pipeline = Pipeline('return "ok"', 'def f(x: str) -> str:', {})
        catalog = PtoolCatalog([])

        report = improve_pipeline(
            pipeline=pipeline,
            result_dirs=[d],
            catalog=catalog,
        )

        assert isinstance(report, ImprovementReport)
        assert report.before_profile.n_cases == 1
        assert len(report.iterations) == 1  # max_iterations defaults to 1
