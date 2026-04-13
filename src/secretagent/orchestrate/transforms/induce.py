"""Induce transform: discover reusable patterns from successful cases."""

from __future__ import annotations

import pathlib
from string import Template

from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.pipeline import Pipeline

_PROMPT_DIR = pathlib.Path(__file__).resolve().parent.parent / 'prompt_templates'

# Ptools consuming at least this fraction of total cost are candidates
# for pattern-based shortcuts.
_COST_FRACTION_THRESHOLD = 0.15


class InduceTransform(PipelineTransform):
    """Discover and codify patterns from successful pipeline runs.

    Analyzes profiling data to identify expensive ptools that might
    benefit from lookup tables or if/elif shortcuts.  When certain
    input patterns consistently lead to the same output, the pipeline
    can short-circuit the LLM call with a direct return.
    """

    name = 'induce'
    requires_llm = True

    def should_apply(self, profile: PipelineProfile) -> bool:
        # Worth trying whenever there are ptools consuming meaningful cost
        return any(
            pp.cost_fraction >= _COST_FRACTION_THRESHOLD
            for pp in profile.ptool_profiles.values()
        )

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        targets = []
        for name, pp in profile.ptool_profiles.items():
            if pp.cost_fraction >= _COST_FRACTION_THRESHOLD:
                targets.append({
                    'ptool': name,
                    'cost_fraction': pp.cost_fraction,
                    'avg_cost': pp.avg_cost,
                    'calls_per_case': pp.calls_per_case,
                    'n_calls': pp.n_calls,
                })

        # Sort by cost fraction descending so the most expensive ptools
        # appear first in the proposal.
        targets.sort(key=lambda t: t['cost_fraction'], reverse=True)

        summary_parts = [
            f'{t["ptool"]} ({t["cost_fraction"]:.0%} of cost, '
            f'{t["n_calls"]} calls)'
            for t in targets
        ]
        return TransformProposal(
            transform_name='induce',
            rationale=(
                f'High-cost ptool(s) that may have repeatable patterns: '
                f'{"; ".join(summary_parts)}. '
                f'Adding lookup tables or if/elif shortcuts for common '
                f'cases could reduce LLM calls and save cost.'
            ),
            changes=targets,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        # Build a description of the ptools targeted for induction
        target_lines = [
            'High-cost ptools to add shortcut logic for:',
        ]
        for change in proposal.changes:
            ptool_name = change['ptool']
            target_lines.append(
                f'  {ptool_name}: cost_fraction={change["cost_fraction"]:.0%}, '
                f'avg_cost=${change["avg_cost"]:.4f}, '
                f'calls_per_case={change["calls_per_case"]:.1f}'
            )

        template = Template((_PROMPT_DIR / 'transform_base.txt').read_text())
        instruction = (
            'Add LOOKUP TABLES or IF/ELIF SHORTCUTS to reduce calls to '
            'the expensive ptools listed below. The goal is to handle '
            'common or predictable cases with direct Python logic '
            'instead of calling the ptool (which invokes an LLM).\n\n'
            'Guidelines:\n'
            '1. Before each expensive ptool call, add if/elif checks for '
            'input patterns that have a known output. For example:\n'
            '   - String matching on keywords in the input\n'
            '   - Lookup dictionaries mapping common inputs to outputs\n'
            '   - Simple rule-based logic that handles obvious cases\n'
            '2. Only fall through to the actual ptool call when no '
            'shortcut matches.\n'
            '3. Keep shortcut logic simple and readable — prefer a dict '
            'lookup or a few if/elif branches over complex code.\n'
            '4. Do NOT remove any ptool calls entirely — they must remain '
            'as the fallback for cases the shortcuts do not cover.\n'
            '5. Do NOT import any modules — use only plain Python and the '
            'available tools.\n\n'
            + '\n'.join(target_lines)
        )

        # Build a focused profiling summary from the proposal data.
        summary_lines = ['Per-ptool cost breakdown (targets for induction):']
        for change in proposal.changes:
            summary_lines.append(
                f'  {change["ptool"]}: cost_frac={change["cost_fraction"]:.0%}, '
                f'avg_cost=${change["avg_cost"]:.4f}, '
                f'calls/case={change["calls_per_case"]:.1f}, '
                f'total_calls={change["n_calls"]}'
            )
        profiling_summary = '\n'.join(summary_lines)

        prompt = template.substitute(
            pipeline_code=pipeline.source,
            profiling_summary=profiling_summary,
            tool_stubs=catalog.render(),
            entry_signature=pipeline.entry_signature,
            transform_instruction=instruction,
        )

        try:
            code = self._generate_code(prompt, pipeline.entry_signature)
            self._validate_code(
                code, pipeline.entry_signature, pipeline._fn.__globals__,
            )
            induced = [c['ptool'] for c in proposal.changes]
            return TransformResult(
                success=True,
                new_pipeline_code=code,
                message=(
                    f'Added pattern-based shortcuts for '
                    f'{", ".join(induced)}.'
                ),
            )
        except Exception as e:
            return TransformResult(
                success=False,
                message=f'Induce failed: {e}',
            )
