#!/usr/bin/env python
# /// script
# dependencies = []
# ///
"""Profile MUSR murder workflow results.

Usage:
    uv run python benchmarks/musr/profile_results.py [GLOB_PATTERN]

Default pattern: results/*.murder_workflow_profiled
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from secretagent.orchestrate.profiler import profile_from_results

pattern = sys.argv[1] if len(sys.argv) > 1 else '*.murder_workflow_profiled'
result_dir = Path(__file__).parent / 'results'
dirs = sorted(result_dir.glob(pattern))

if not dirs:
    print(f'No result dirs matching {pattern} in {result_dir}')
    sys.exit(1)

print(f'Profiling {len(dirs)} dir(s): {[d.name for d in dirs]}')
profile = profile_from_results(dirs)

print(f'\nCases: {profile.n_cases}')
print(f'Cases with rollout: {profile.n_cases_with_rollout}')
print(f'Accuracy: {profile.accuracy:.2%}')
print(f'Total cost: ${profile.total_cost:.4f}')
print(f'Avg cost: ${profile.avg_cost:.4f}')
print(f'Avg latency: {profile.avg_latency:.1f}s')
print(f'\nPtools profiled: {list(profile.ptool_profiles.keys())}')

total_frac = 0
for name, pp in profile.ptool_profiles.items():
    print(f'\n  {name}:')
    print(f'    calls/case={pp.calls_per_case:.1f}, n_calls={pp.n_calls}')
    print(f'    cost_frac={pp.cost_fraction:.1%}, avg_cost=${pp.avg_cost:.4f}')
    print(f'    avg_latency={pp.avg_latency:.1f}s')
    print(f'    avg_tokens_in={pp.avg_tokens_in:.0f}, avg_tokens_out={pp.avg_tokens_out:.0f}')
    print(f'    presence_in_correct={pp.presence_in_correct:.2%}')
    print(f'    presence_in_incorrect={pp.presence_in_incorrect:.2%}')
    print(f'    exception_rate={pp.exception_rate:.2%}')
    if pp.error_patterns:
        print(f'    errors: {len(pp.error_patterns)} pattern(s), '
              f'total={sum(e.frequency for e in pp.error_patterns)}')
    total_frac += pp.cost_fraction

print(f'\nCost fractions sum: {total_frac:.4f}')
