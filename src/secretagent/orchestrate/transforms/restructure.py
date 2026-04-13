"""Restructure transform: reorganize the overall pipeline flow."""

from __future__ import annotations

import pathlib
from string import Template

from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
    format_profiling_summary,
)
from secretagent.orchestrate.pipeline import Pipeline

_PROMPT_DIR = pathlib.Path(__file__).resolve().parent.parent / 'prompt_templates'


class RestructureTransform(PipelineTransform):
    """Reorganize the pipeline's control flow and tool call ordering.

    Analyzes profiling data to identify opportunities for:
    - Reordering tool calls so cheap/fast checks run first
    - Adding early exits when a cheap check is sufficient
    - Caching repeated intermediate results
    - Improving error recovery paths
    """

    name = 'restructure'
    requires_llm = True

    def should_apply(self, profile: PipelineProfile) -> bool:
        return True  # restructuring is always worth considering

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        # Sort ptools by cost (ascending) to identify cheap-first reordering
        ptools_by_cost = sorted(
            profile.ptool_profiles.values(),
            key=lambda pp: pp.avg_cost,
        )

        changes: list[dict] = []
        rationale_parts: list[str] = []

        # 1. Identify reordering opportunities: cheap ptools with high lift
        #    should run before expensive ones
        if len(ptools_by_cost) >= 2:
            cheapest = ptools_by_cost[0]
            most_expensive = ptools_by_cost[-1]
            if most_expensive.avg_cost > 0 and cheapest.avg_cost > 0:
                cost_ratio = most_expensive.avg_cost / cheapest.avg_cost
                if cost_ratio > 2.0:
                    changes.append({
                        'type': 'reorder',
                        'detail': (
                            f'Move cheap calls first: '
                            f'{cheapest.name} (${cheapest.avg_cost:.4f}) '
                            f'before {most_expensive.name} '
                            f'(${most_expensive.avg_cost:.4f}), '
                            f'cost ratio {cost_ratio:.1f}x'
                        ),
                    })
                    rationale_parts.append(
                        f'reorder calls ({cheapest.name} is '
                        f'{cost_ratio:.1f}x cheaper than '
                        f'{most_expensive.name})'
                    )

        # 2. Identify early-exit candidates: cheap ptools with high
        #    accuracy_when_correct could short-circuit expensive calls
        for pp in ptools_by_cost:
            if (pp.avg_cost < profile.avg_cost * 0.3
                    and pp.accuracy_when_correct > 0.7):
                changes.append({
                    'type': 'early_exit',
                    'ptool': pp.name,
                    'avg_cost': round(pp.avg_cost, 6),
                    'accuracy_when_correct': round(
                        pp.accuracy_when_correct, 3,
                    ),
                })
                rationale_parts.append(
                    f'add early exit via {pp.name} '
                    f'(cheap, accuracy_when_correct='
                    f'{pp.accuracy_when_correct:.0%})'
                )

        # 3. Identify caching opportunities: ptools called more than once
        #    per case on average
        for pp in profile.ptool_profiles.values():
            if pp.calls_per_case > 1.3:
                changes.append({
                    'type': 'cache',
                    'ptool': pp.name,
                    'calls_per_case': round(pp.calls_per_case, 1),
                    'avg_cost': round(pp.avg_cost, 6),
                    'potential_savings': round(
                        pp.avg_cost * (pp.calls_per_case - 1), 6,
                    ),
                })
                rationale_parts.append(
                    f'cache {pp.name} '
                    f'({pp.calls_per_case:.1f} calls/case)'
                )

        # 4. Identify error recovery improvements: ptools with errors
        #    that also have high cost
        for pp in profile.ptool_profiles.values():
            err_count = sum(e.frequency for e in pp.error_patterns)
            if err_count > 0 and pp.cost_fraction > 0.1:
                changes.append({
                    'type': 'error_recovery',
                    'ptool': pp.name,
                    'error_count': err_count,
                    'cost_fraction': round(pp.cost_fraction, 3),
                })
                rationale_parts.append(
                    f'improve error recovery for {pp.name} '
                    f'({err_count} errors, '
                    f'{pp.cost_fraction:.0%} of cost)'
                )

        if not rationale_parts:
            rationale_parts.append(
                'general restructuring for efficiency'
            )

        return TransformProposal(
            transform_name='restructure',
            rationale=(
                f'Restructure pipeline to: '
                f'{"; ".join(rationale_parts)}.'
            ),
            changes=changes,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        # Build structured guidance from the proposal changes
        guidance_lines: list[str] = []

        reorder_changes = [
            c for c in proposal.changes if c.get('type') == 'reorder'
        ]
        early_exit_changes = [
            c for c in proposal.changes if c.get('type') == 'early_exit'
        ]
        cache_changes = [
            c for c in proposal.changes if c.get('type') == 'cache'
        ]
        error_recovery_changes = [
            c for c in proposal.changes
            if c.get('type') == 'error_recovery'
        ]

        if reorder_changes:
            guidance_lines.append(
                'REORDERING: Move cheap/fast tool calls before '
                'expensive ones so the pipeline can exit early '
                'when a cheap check suffices:'
            )
            for c in reorder_changes:
                guidance_lines.append(f'  - {c["detail"]}')

        if early_exit_changes:
            guidance_lines.append(
                '\nEARLY EXITS: When a cheap tool gives a '
                'high-confidence answer, return immediately '
                'without calling expensive tools:'
            )
            for c in early_exit_changes:
                guidance_lines.append(
                    f'  - {c["ptool"]} '
                    f'(cost=${c["avg_cost"]:.4f}, '
                    f'accuracy_when_correct='
                    f'{c["accuracy_when_correct"]:.0%}): '
                    f'if its result is confident/clear, use it '
                    f'as the final answer'
                )

        if cache_changes:
            guidance_lines.append(
                '\nCACHING: Store intermediate results in local '
                'variables to avoid redundant calls:'
            )
            for c in cache_changes:
                guidance_lines.append(
                    f'  - {c["ptool"]} is called '
                    f'{c["calls_per_case"]:.1f}x per case '
                    f'(avg cost=${c["avg_cost"]:.4f}). '
                    f'Cache its result and reuse it '
                    f'(saves ~${c["potential_savings"]:.4f}/case)'
                )

        if error_recovery_changes:
            guidance_lines.append(
                '\nERROR RECOVERY: Add fallback paths for tools '
                'that fail frequently and consume significant cost:'
            )
            for c in error_recovery_changes:
                guidance_lines.append(
                    f'  - {c["ptool"]} '
                    f'({c["error_count"]} errors, '
                    f'{c["cost_fraction"]:.0%} of cost): '
                    f'wrap in try/except with a simpler fallback'
                )

        if not guidance_lines:
            guidance_lines.append(
                'General restructuring: reorder tool calls so '
                'cheaper/faster checks run first, add early exits '
                'when a definitive answer is available, and cache '
                'any repeated intermediate results.'
            )

        template = Template(
            (_PROMPT_DIR / 'transform_base.txt').read_text(),
        )
        instruction = (
            'RESTRUCTURE the pipeline for better efficiency. '
            'Reorganize the control flow following these '
            'specific guidelines:\n\n'
            + '\n'.join(guidance_lines)
            + '\n\nGeneral rules:\n'
            '1. Run the CHEAPEST tool calls first — if a cheap '
            'check can determine the answer, skip expensive calls\n'
            '2. Add early returns when a tool gives a clear, '
            'high-confidence result\n'
            '3. Store intermediate results in variables rather '
            'than calling the same tool twice with the same input\n'
            '4. Add try/except around unreliable tools with '
            'sensible fallbacks\n'
            '5. Preserve the overall logic and return type — the '
            'restructured pipeline must produce the same kind of '
            'answer\n'
            '6. Do NOT remove any tool calls entirely (that is '
            'pruning, not restructuring) — just reorder, guard, '
            'and cache them'
        )

        prompt = template.substitute(
            pipeline_code=pipeline.source,
            profiling_summary=format_profiling_summary(
                PipelineProfile(accuracy=0.0, ptool_profiles={}),
            ),
            tool_stubs=catalog.render(),
            entry_signature=pipeline.entry_signature,
            transform_instruction=instruction,
        )

        try:
            code = self._generate_code(prompt, pipeline.entry_signature)
            self._validate_code(
                code, pipeline.entry_signature, pipeline._fn.__globals__,
            )
            change_types = sorted(
                {c.get('type', 'restructure') for c in proposal.changes},
            )
            return TransformResult(
                success=True,
                new_pipeline_code=code,
                message=(
                    f'Restructured pipeline '
                    f'({", ".join(change_types or ["general"])}).'
                ),
            )
        except Exception as e:
            return TransformResult(
                success=False,
                message=f'Restructure failed: {e}',
            )
