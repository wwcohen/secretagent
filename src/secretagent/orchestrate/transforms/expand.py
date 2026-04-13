"""Expand transform: decompose underperforming ptools into sub-steps."""

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


class ExpandTransform(PipelineTransform):
    """Break apart expensive, underperforming ptools into smaller steps.

    Implementation guide:
    When a ptool consumes high cost but correlates poorly with correct
    answers, generate a replacement sub-pipeline that decomposes its
    task into multiple cheaper steps.
    """

    name = 'expand'
    requires_llm = True

    def should_apply(self, profile: PipelineProfile) -> bool:
        return any(
            pp.cost_fraction > 0.3 and pp.accuracy_when_correct < profile.accuracy * 0.8
            for pp in profile.ptool_profiles.values()
        )

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        targets = []
        for name, pp in profile.ptool_profiles.items():
            if pp.cost_fraction > 0.3 and pp.accuracy_when_correct < profile.accuracy * 0.8:
                targets.append({
                    'ptool': name,
                    'cost_fraction': round(pp.cost_fraction, 3),
                    'accuracy_when_correct': round(pp.accuracy_when_correct, 3),
                    'avg_cost': round(pp.avg_cost, 6),
                    'avg_tokens_in': round(pp.avg_tokens_in, 0),
                    'avg_tokens_out': round(pp.avg_tokens_out, 0),
                    'calls_per_case': round(pp.calls_per_case, 1),
                })

        summary_parts = [
            f'{t["ptool"]} (cost={t["cost_fraction"]:.0%}, '
            f'accuracy_when_correct={t["accuracy_when_correct"]:.0%})'
            for t in targets
        ]
        return TransformProposal(
            transform_name='expand',
            rationale=(
                f'Expensive underperforming ptool(s): {", ".join(summary_parts)}. '
                f'Decomposing into cheaper focused sub-steps to improve '
                f'cost-effectiveness.'
            ),
            changes=targets,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        # Build per-ptool expansion guidance for the prompt
        expand_lines = [
            'Ptools to EXPAND into multiple cheaper, focused sub-steps:'
        ]
        for change in proposal.changes:
            ptool_name = change['ptool']
            expand_lines.append(
                f'\n  {ptool_name} '
                f'(cost_fraction={change["cost_fraction"]:.0%}, '
                f'accuracy_when_correct={change["accuracy_when_correct"]:.0%}, '
                f'avg_cost=${change["avg_cost"]:.4f}, '
                f'avg_tokens_in={change["avg_tokens_in"]:.0f}, '
                f'avg_tokens_out={change["avg_tokens_out"]:.0f})'
            )

        template = Template((_PROMPT_DIR / 'transform_base.txt').read_text())
        instruction = (
            'DECOMPOSE the expensive underperforming ptool call(s) listed below '
            'into multiple CHEAPER, FOCUSED sub-steps. The goal is to replace '
            'one expensive call that tries to do too much with several smaller '
            'calls that each handle a specific part of the task.\n\n'
            'Guidelines:\n'
            '1. If a ptool does both reasoning and extraction in one call, '
            'split it into separate reasoning and extraction steps\n'
            '2. Replace a single broad prompt with a sequence of narrower, '
            'focused prompts that each do one thing well\n'
            '3. Use the available tools from the catalog — pick simpler '
            'tools when they suffice for a sub-step\n'
            '4. Each sub-step should pass its result to the next step '
            'as concrete input, not re-derive it\n'
            '5. The total cost of the sub-steps should be less than the '
            'original single call\n'
            '6. Keep the overall pipeline logic and return value unchanged\n\n'
            + '\n'.join(expand_lines)
        )

        prompt = template.substitute(
            pipeline_code=pipeline.source,
            profiling_summary=format_profiling_summary(
                PipelineProfile(
                    accuracy=0.0,
                    ptool_profiles={},
                ),
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
            expanded = [c['ptool'] for c in proposal.changes]
            return TransformResult(
                success=True,
                new_pipeline_code=code,
                message=(
                    f'Expanded {", ".join(expanded)} into focused sub-steps.'
                ),
            )
        except Exception as e:
            return TransformResult(
                success=False,
                message=f'Expand failed: {e}',
            )
