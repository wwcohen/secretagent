"""Artificial Analysis model data: benchmarks, pricing, speed.

Wraps the free AA API (https://artificialanalysis.ai/) with caching
to provide benchmark and pricing metadata for LLM models.  Used by
upgrade/downgrade transforms and the compare_models ptool.

Data source attribution: https://artificialanalysis.ai/
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from pydantic import BaseModel

from secretagent.cache_util import cached

log = logging.getLogger(__name__)

AA_API_URL = 'https://artificialanalysis.ai/api/v2/data/llms/models'


class ModelInfo(BaseModel):
    """Benchmark, pricing, and speed data for a single model."""

    aa_id: str
    name: str
    slug: str
    creator: str
    # Benchmarks (not all models have all scores)
    intelligence_index: float | None = None
    coding_index: float | None = None
    math_index: float | None = None
    mmlu_pro: float | None = None
    gpqa: float | None = None
    livecodebench: float | None = None
    # Pricing (per 1M tokens, USD)
    input_price: float | None = None
    output_price: float | None = None
    blended_price: float | None = None
    # Speed
    output_tokens_per_second: float | None = None
    time_to_first_token: float | None = None


def _normalize_name(name: str) -> str:
    """Normalize a model name for fuzzy matching.

    Handles litellm format (together_ai/deepseek-ai/DeepSeek-V3.1)
    and AA slugs (deepseek-v3-1).
    """
    # Take last path segment if slashes present
    base = name.split('/')[-1]
    # Lowercase, replace dots/underscores with hyphens
    base = base.lower().replace('.', '-').replace('_', '-')
    # Strip common suffixes that don't affect identity
    for suffix in ['-tput', '-fp8']:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base


def _fetch_aa_models_raw() -> dict[str, Any]:
    """Fetch model data from the Artificial Analysis API.

    Returns the raw JSON response dict, or empty dict on failure.
    Meant to be wrapped with cached() at call site.
    """
    import httpx

    api_key = os.environ.get('ARTIFICIAL_ANALYSIS_API_KEY', '')
    if not api_key:
        log.debug('ARTIFICIAL_ANALYSIS_API_KEY not set; AA data unavailable')
        return {}
    try:
        resp = httpx.get(
            AA_API_URL,
            headers={'x-api-key': api_key},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning('Failed to fetch AA model data: %s', e)
        return {}


def _parse_model_info(raw: dict) -> ModelInfo:
    """Extract ModelInfo from a single AA API response entry."""
    evals = raw.get('evaluations') or {}
    pricing = raw.get('pricing') or {}
    creator = raw.get('model_creator') or {}
    return ModelInfo(
        aa_id=raw.get('id', ''),
        name=raw.get('name', ''),
        slug=raw.get('slug', ''),
        creator=creator.get('name', ''),
        intelligence_index=evals.get('artificial_analysis_intelligence_index'),
        coding_index=evals.get('artificial_analysis_coding_index'),
        math_index=evals.get('artificial_analysis_math_index'),
        mmlu_pro=evals.get('mmlu_pro'),
        gpqa=evals.get('gpqa'),
        livecodebench=evals.get('livecodebench'),
        input_price=pricing.get('price_1m_input_tokens'),
        output_price=pricing.get('price_1m_output_tokens'),
        blended_price=pricing.get('price_1m_blended_3_to_1'),
        output_tokens_per_second=raw.get('median_output_tokens_per_second'),
        time_to_first_token=raw.get('median_time_to_first_token_seconds'),
    )


def fetch_all_models() -> dict[str, ModelInfo]:
    """Fetch and parse all models from AA, with disk caching.

    Returns dict keyed by normalized name for fast lookup.
    """
    response = cached(_fetch_aa_models_raw)()
    data = response.get('data', []) if isinstance(response, dict) else []
    result: dict[str, ModelInfo] = {}
    for raw in data:
        info = _parse_model_info(raw)
        # Index by both normalized name and slug for flexible lookup
        result[_normalize_name(info.name)] = info
        result[_normalize_name(info.slug)] = info
    return result


def lookup_model(litellm_model: str) -> ModelInfo | None:
    """Find AA data for a litellm model string.

    Accepts formats like 'together_ai/deepseek-ai/DeepSeek-V3.1'
    or just 'DeepSeek-V3.1'.
    """
    all_models = fetch_all_models()
    if not all_models:
        return None

    base = litellm_model.split('/')[-1]
    normalized = _normalize_name(base)

    # Exact normalized match
    if normalized in all_models:
        return all_models[normalized]

    # Substring containment fallback
    for key, info in all_models.items():
        if normalized in key or key in normalized:
            return info

    return None


def _fmt(val: float | None, fmt: str = '.1f', prefix: str = '', suffix: str = '') -> str:
    """Format a nullable float, returning '—' if None."""
    if val is None:
        return '—'
    return f'{prefix}{val:{fmt}}{suffix}'


def format_model_comparison(a: ModelInfo, b: ModelInfo) -> str:
    """Format a side-by-side comparison of two models."""
    rows = [
        ('Model', a.name, b.name),
        ('Creator', a.creator, b.creator),
        ('Intelligence Index', _fmt(a.intelligence_index), _fmt(b.intelligence_index)),
        ('Coding Index', _fmt(a.coding_index), _fmt(b.coding_index)),
        ('Math Index', _fmt(a.math_index), _fmt(b.math_index)),
        ('MMLU-Pro', _fmt(a.mmlu_pro, '.3f'), _fmt(b.mmlu_pro, '.3f')),
        ('GPQA', _fmt(a.gpqa, '.3f'), _fmt(b.gpqa, '.3f')),
        ('LiveCodeBench', _fmt(a.livecodebench, '.3f'), _fmt(b.livecodebench, '.3f')),
        ('Input $/1M tokens', _fmt(a.input_price, '.2f', '$'), _fmt(b.input_price, '.2f', '$')),
        ('Output $/1M tokens', _fmt(a.output_price, '.2f', '$'), _fmt(b.output_price, '.2f', '$')),
        ('Blended $/1M tokens', _fmt(a.blended_price, '.2f', '$'), _fmt(b.blended_price, '.2f', '$')),
        ('Output tok/s', _fmt(a.output_tokens_per_second, '.0f'), _fmt(b.output_tokens_per_second, '.0f')),
        ('TTFT (s)', _fmt(a.time_to_first_token, '.2f'), _fmt(b.time_to_first_token, '.2f')),
    ]
    # Compute column widths
    w0 = max(len(r[0]) for r in rows)
    w1 = max(len(r[1]) for r in rows)
    w2 = max(len(r[2]) for r in rows)

    lines = []
    for label, va, vb in rows:
        lines.append(f'{label:<{w0}}  {va:>{w1}}  {vb:>{w2}}')
    lines.append('')
    lines.append('Data: https://artificialanalysis.ai/')
    return '\n'.join(lines)


def format_model_summary(info: ModelInfo) -> str:
    """One-line summary of a model's key metrics."""
    parts = [info.name]
    if info.intelligence_index is not None:
        parts.append(f'intelligence={info.intelligence_index:.1f}')
    if info.coding_index is not None:
        parts.append(f'coding={info.coding_index:.1f}')
    if info.blended_price is not None:
        parts.append(f'${info.blended_price:.2f}/1M')
    if info.output_tokens_per_second is not None:
        parts.append(f'{info.output_tokens_per_second:.0f} tok/s')
    return ', '.join(parts)
