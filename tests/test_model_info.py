"""Tests for Artificial Analysis model info integration."""

from unittest.mock import patch

import pytest

from secretagent.orchestrate.model_info import (
    ModelInfo, _normalize_name, _parse_model_info, lookup_model,
    fetch_all_models, format_model_comparison, format_model_summary,
)


# ── Normalize name ──────────────────────────────────────────────────

class TestNormalizeName:
    def test_litellm_last_segment(self):
        assert _normalize_name('DeepSeek-V3.1') == 'deepseek-v3-1'

    def test_slug_passthrough(self):
        assert _normalize_name('deepseek-v3-1') == 'deepseek-v3-1'

    def test_strips_tput_suffix(self):
        result = _normalize_name('Qwen3-235B-A22B-Instruct-2507-tput')
        assert result == 'qwen3-235b-a22b-instruct-2507'

    def test_strips_fp8_suffix(self):
        result = _normalize_name('Qwen3-Coder-Next-FP8')
        assert result == 'qwen3-coder-next'

    def test_underscores_to_hyphens(self):
        assert _normalize_name('gpt_oss_20b') == 'gpt-oss-20b'


# ── Lookup model ────────────────────────────────────────────────────

FAKE_AA_RESPONSE = {
    'status': 200,
    'data': [
        {
            'id': 'abc-123',
            'name': 'DeepSeek V3.1',
            'slug': 'deepseek-v3-1',
            'model_creator': {'id': 'ds', 'name': 'DeepSeek', 'slug': 'deepseek'},
            'evaluations': {
                'artificial_analysis_intelligence_index': 58.0,
                'artificial_analysis_coding_index': 52.3,
                'artificial_analysis_math_index': 75.0,
                'mmlu_pro': 0.82,
                'gpqa': None,
                'livecodebench': 0.55,
            },
            'pricing': {
                'price_1m_input_tokens': 0.60,
                'price_1m_output_tokens': 1.70,
                'price_1m_blended_3_to_1': 0.875,
            },
            'median_output_tokens_per_second': 120.5,
            'median_time_to_first_token_seconds': 0.8,
        },
        {
            'id': 'def-456',
            'name': 'Qwen3.5-9B',
            'slug': 'qwen3-5-9b',
            'model_creator': {'id': 'qw', 'name': 'Qwen', 'slug': 'qwen'},
            'evaluations': {
                'artificial_analysis_intelligence_index': 35.0,
                'artificial_analysis_coding_index': 30.0,
            },
            'pricing': {
                'price_1m_input_tokens': 0.10,
                'price_1m_output_tokens': 0.15,
                'price_1m_blended_3_to_1': 0.1125,
            },
            'median_output_tokens_per_second': 200.0,
            'median_time_to_first_token_seconds': 0.3,
        },
    ],
}


def _build_fake_index():
    """Build the lookup dict that fetch_all_models() would return."""
    result = {}
    for raw in FAKE_AA_RESPONSE['data']:
        info = _parse_model_info(raw)
        result[_normalize_name(info.name)] = info
        result[_normalize_name(info.slug)] = info
    return result


class TestLookupModel:
    @patch('secretagent.orchestrate.model_info.fetch_all_models')
    def test_finds_by_litellm_string(self, mock_fetch):
        mock_fetch.return_value = _build_fake_index()
        result = lookup_model('together_ai/deepseek-ai/DeepSeek-V3.1')
        assert result is not None
        assert result.name == 'DeepSeek V3.1'
        assert result.intelligence_index == 58.0

    @patch('secretagent.orchestrate.model_info.fetch_all_models')
    def test_finds_by_base_name(self, mock_fetch):
        mock_fetch.return_value = _build_fake_index()
        result = lookup_model('Qwen3.5-9B')
        assert result is not None
        assert result.name == 'Qwen3.5-9B'

    @patch('secretagent.orchestrate.model_info.fetch_all_models')
    def test_returns_none_for_unknown(self, mock_fetch):
        mock_fetch.return_value = _build_fake_index()
        assert lookup_model('nonexistent-model-xyz') is None

    @patch('secretagent.orchestrate.model_info.fetch_all_models')
    def test_returns_none_when_api_unavailable(self, mock_fetch):
        mock_fetch.return_value = {}
        assert lookup_model('DeepSeek-V3.1') is None


# ── Format functions ────────────────────────────────────────────────

class TestFormatModelComparison:
    def test_produces_readable_output(self):
        a = ModelInfo(
            aa_id='1', name='Model A', slug='a', creator='X',
            intelligence_index=80.0, input_price=1.0, output_price=3.0,
            blended_price=1.5,
        )
        b = ModelInfo(
            aa_id='2', name='Model B', slug='b', creator='Y',
            intelligence_index=90.0, input_price=2.0, output_price=5.0,
            blended_price=2.75,
        )
        result = format_model_comparison(a, b)
        assert 'Model A' in result
        assert 'Model B' in result
        assert '80.0' in result
        assert '90.0' in result
        assert 'artificialanalysis.ai' in result

    def test_handles_none_values(self):
        a = ModelInfo(aa_id='1', name='Sparse', slug='s', creator='X')
        b = ModelInfo(aa_id='2', name='Full', slug='f', creator='Y',
                      intelligence_index=50.0, input_price=1.0)
        result = format_model_comparison(a, b)
        assert '—' in result  # None values rendered as dash


class TestFormatModelSummary:
    def test_includes_key_metrics(self):
        info = ModelInfo(
            aa_id='1', name='TestModel', slug='t', creator='X',
            intelligence_index=60.0, coding_index=45.0,
            blended_price=1.5, output_tokens_per_second=100.0,
        )
        result = format_model_summary(info)
        assert 'TestModel' in result
        assert 'intelligence=60.0' in result
        assert 'coding=45.0' in result
        assert '$1.50/1M' in result
        assert '100 tok/s' in result

    def test_omits_none_fields(self):
        info = ModelInfo(aa_id='1', name='Minimal', slug='m', creator='X')
        result = format_model_summary(info)
        assert result == 'Minimal'
