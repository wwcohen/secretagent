"""Profiler wrapped as @interface ptools — FREE (no API calls).

These interfaces let the big model (or any pipeline) query profiling
data by calling them as regular ptools.  They read results.jsonl files
and return human-readable summaries.
"""

from secretagent.core import interface
from secretagent.orchestrate.profiler import profile_from_results
from secretagent.orchestrate.transforms.base import format_profiling_summary


@interface
def profile_pipeline(result_dirs: list, pipeline_source: str = '') -> str:
    """Profile a pipeline from experiment result directories.

    Reads results.jsonl files to compute per-ptool metrics:
    cost_fraction, accuracy correlations, error_patterns, token saturation.

    This is FREE — no API calls, just file reads.  Call it often.

    Args:
        result_dirs: list of directory paths containing results.jsonl
        pipeline_source: optional source code of the pipeline

    Returns:
        Human-readable profiling summary with per-ptool breakdown.
    """
    profile = profile_from_results(result_dirs, pipeline_source=pipeline_source)
    return format_profiling_summary(profile)


@interface
def identify_weakest_ptool(result_dirs: list) -> str:
    """Identify the worst-performing ptool from profiling data.

    Ranks ptools by improvement potential:
    - Ptools that appear in incorrect cases more than correct ones
    - Ptools with error patterns
    - Ptools consuming disproportionate cost

    This is FREE — no API calls.

    Args:
        result_dirs: list of directory paths containing results.jsonl

    Returns:
        Name and metrics of the weakest ptool(s), one per line.
    """
    profile = profile_from_results(result_dirs)
    if not profile.ptool_profiles:
        return 'No ptool data available (ensure evaluate.record_details=true)'

    # Score each ptool: higher = more worth improving
    skip_utilities = {'extract_index', 'raw_answer', 'format_answer'}
    scored = []
    for name, pp in profile.ptool_profiles.items():
        if pp.n_calls < 3 or name in skip_utilities:
            continue
        error_count = sum(e.frequency for e in pp.error_patterns)
        error_rate = error_count / pp.n_calls if pp.n_calls else 0.0
        # Prefer high-cost ptools (where improvement has impact)
        weakness = pp.cost_fraction + error_rate * 0.5
        scored.append((name, weakness, pp))

    if not scored:
        return 'No ptools with sufficient data to analyze.'

    scored.sort(key=lambda x: x[1], reverse=True)

    lines = [f'Pipeline accuracy: {profile.accuracy:.1%}\n']
    for name, weakness, pp in scored:
        error_count = sum(e.frequency for e in pp.error_patterns)
        lines.append(
            f'{name}: weakness={weakness:.3f}, '
            f'cost_frac={pp.cost_fraction:.1%}, '
            f'errors={error_count}, '
            f'presence_correct={pp.presence_in_correct:.2f}, '
            f'presence_incorrect={pp.presence_in_incorrect:.2f}, '
            f'exception_rate={pp.exception_rate:.2f}'
        )
    return '\n'.join(lines)
