"""Pipeline profiler: per-ptool cost/accuracy/latency metrics from results."""

from __future__ import annotations

import json
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel

from secretagent import savefile


class ErrorPattern(BaseModel):
    pattern: str
    frequency: int
    example_cases: list[dict[str, Any]] = []


class PtoolProfile(BaseModel):
    name: str
    n_calls: int = 0
    calls_per_case: float = 0.0
    avg_cost: float = 0.0
    avg_latency: float = 0.0
    avg_tokens_in: float = 0.0
    avg_tokens_out: float = 0.0
    max_tokens_out: int = 0
    output_token_saturation: float = 0.0  # max_tokens_out / configured limit
    cost_fraction: float = 0.0
    presence_in_correct: float = 0.0
    presence_in_incorrect: float = 0.0
    exception_rate: float = 0.0
    n_exceptions: int = 0
    lift: float | None = None
    error_patterns: list[ErrorPattern] = []


class PipelineProfile(BaseModel):
    pipeline_source: str | None = None
    accuracy: float = 0.0
    total_cost: float = 0.0
    avg_cost: float = 0.0
    total_latency: float = 0.0
    avg_latency: float = 0.0
    n_cases: int = 0
    n_cases_with_rollout: int = 0
    ptool_profiles: dict[str, PtoolProfile] = {}


def profile_from_results(
    result_dirs: Sequence[str | Path],
    pipeline_source: str | None = None,
    latest: int = 0,
    check: list[str] | None = None,
    max_output_tokens: int | None = None,
) -> PipelineProfile:
    """Build a PipelineProfile from experiment result directories.

    Args:
        result_dirs: directories containing results.jsonl files
        pipeline_source: optional source code of the pipeline
        latest: keep latest k dirs per tag (0 = all)
        check: config constraint dotlist for filtering
        max_output_tokens: configured token limit (for saturation calculation).
            If None, reads from config 'llm.max_tokens'.
    """
    if max_output_tokens is None:
        from secretagent import config
        max_output_tokens = config.get('llm.max_tokens') or 0
    dirs = savefile.filter_paths(result_dirs, latest=latest, dotlist=check or [])

    # Accumulators
    n_cases = 0
    n_correct = 0
    total_cost = 0.0
    total_latency = 0.0
    n_cases_with_rollout = 0

    # Per-ptool accumulators
    ptool_total_cost: dict[str, float] = defaultdict(float)
    ptool_total_latency: dict[str, float] = defaultdict(float)
    ptool_total_tokens_in: dict[str, int] = defaultdict(int)
    ptool_total_tokens_out: dict[str, int] = defaultdict(int)
    ptool_n_calls: dict[str, int] = defaultdict(int)
    ptool_correct_cases: dict[str, int] = defaultdict(int)
    ptool_incorrect_cases: dict[str, int] = defaultdict(int)
    ptool_max_tokens_out: dict[str, int] = defaultdict(int)
    ptool_n_exceptions: dict[str, int] = defaultdict(int)
    ptool_errors: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cases_correct_total = 0
    cases_incorrect_total = 0

    for d in dirs:
        jsonl_path = Path(d) / 'results.jsonl'
        if not jsonl_path.exists():
            warnings.warn(f'No results.jsonl in {d}, skipping')
            continue
        with open(jsonl_path) as f:
            for line in f:
                record = json.loads(line)
                n_cases += 1
                correct = record.get('correct', False)
                total_cost += record.get('cost', 0.0)
                total_latency += record.get('latency', 0.0)
                if correct:
                    n_correct += 1

                rollout = record.get('rollout')
                if not rollout:
                    continue
                n_cases_with_rollout += 1
                if correct:
                    cases_correct_total += 1
                else:
                    cases_incorrect_total += 1

                # Track which ptools appeared in this case
                ptools_in_case: set[str] = set()
                for step in rollout:
                    func = step.get('func', '')
                    stats = step.get('stats') or {}
                    ptools_in_case.add(func)
                    ptool_n_calls[func] += 1
                    ptool_total_cost[func] += stats.get('cost', 0.0)
                    ptool_total_latency[func] += stats.get('latency', 0.0)
                    ptool_total_tokens_in[func] += stats.get('input_tokens', 0)
                    out_tokens = stats.get('output_tokens', 0)
                    ptool_total_tokens_out[func] += out_tokens
                    if out_tokens > ptool_max_tokens_out[func]:
                        ptool_max_tokens_out[func] = out_tokens

                    # Detect errors
                    output = step.get('output')
                    if isinstance(output, str) and output.startswith('**exception'):
                        ptool_n_exceptions[func] += 1
                        ptool_errors[func].append({
                            'output': output,
                            'args': step.get('args'),
                        })

                for func in ptools_in_case:
                    if correct:
                        ptool_correct_cases[func] += 1
                    else:
                        ptool_incorrect_cases[func] += 1

    # Build per-ptool profiles
    all_ptools = set(ptool_n_calls.keys())
    pipeline_total_cost = sum(ptool_total_cost.values()) or 1.0  # avoid div-by-zero
    ptool_profiles: dict[str, PtoolProfile] = {}

    for name in sorted(all_ptools):
        nc = ptool_n_calls[name]
        ptool_profiles[name] = PtoolProfile(
            name=name,
            n_calls=nc,
            calls_per_case=nc / n_cases_with_rollout if n_cases_with_rollout else 0.0,
            avg_cost=ptool_total_cost[name] / nc if nc else 0.0,
            avg_latency=ptool_total_latency[name] / nc if nc else 0.0,
            avg_tokens_in=ptool_total_tokens_in[name] / nc if nc else 0.0,
            avg_tokens_out=ptool_total_tokens_out[name] / nc if nc else 0.0,
            max_tokens_out=ptool_max_tokens_out[name],
            output_token_saturation=(
                ptool_max_tokens_out[name] / max_output_tokens
                if max_output_tokens else 0.0
            ),
            cost_fraction=ptool_total_cost[name] / pipeline_total_cost,
            presence_in_correct=(
                ptool_correct_cases[name] / cases_correct_total
                if cases_correct_total else 0.0
            ),
            presence_in_incorrect=(
                ptool_incorrect_cases[name] / cases_incorrect_total
                if cases_incorrect_total else 0.0
            ),
            exception_rate=ptool_n_exceptions[name] / nc if nc else 0.0,
            n_exceptions=ptool_n_exceptions[name],
            error_patterns=_detect_error_patterns(ptool_errors.get(name, [])),
        )

    return PipelineProfile(
        pipeline_source=pipeline_source,
        accuracy=n_correct / n_cases if n_cases else 0.0,
        total_cost=total_cost,
        avg_cost=total_cost / n_cases if n_cases else 0.0,
        total_latency=total_latency,
        avg_latency=total_latency / n_cases if n_cases else 0.0,
        n_cases=n_cases,
        n_cases_with_rollout=n_cases_with_rollout,
        ptool_profiles=ptool_profiles,
    )


def compute_lift(
    profile_with: PipelineProfile,
    profile_without: PipelineProfile,
    ptool_name: str,
) -> float | None:
    """Compare accuracy between two profiles for a ptool.

    Returns accuracy difference, or None if either profile lacks data.
    """
    if (ptool_name not in profile_with.ptool_profiles
            or ptool_name not in profile_without.ptool_profiles):
        return None
    return profile_with.accuracy - profile_without.accuracy


def _detect_error_patterns(error_outputs: list[dict[str, Any]]) -> list[ErrorPattern]:
    """Group errors by prefix similarity, return top patterns."""
    if not error_outputs:
        return []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for err in error_outputs:
        msg = err.get('output', '')
        # Group by first 80 chars of the error message
        prefix = msg[:80]
        groups[prefix].append(err)

    patterns = []
    for prefix, examples in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        patterns.append(ErrorPattern(
            pattern=prefix,
            frequency=len(examples),
            example_cases=examples[:3],
        ))
    return patterns
