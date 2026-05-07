"""Repair transform: fix ptools that produce frequent errors."""

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


class RepairTransform(PipelineTransform):
    """Fix ptools with recurring error patterns.

    Analyzes error_patterns from the profiler to identify common failure
    modes. Asks an LLM to add error handling (try/except, fallbacks,
    input validation) around the failing ptool calls.
    """

    name = 'repair'
    requires_llm = True

    def should_apply(self, profile: PipelineProfile) -> bool:
        return any(
            pp.error_patterns
            for pp in profile.ptool_profiles.values()
        )

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        targets = []
        for name, pp in profile.ptool_profiles.items():
            if pp.error_patterns:
                total_errors = sum(ep.frequency for ep in pp.error_patterns)
                top_patterns = [
                    ep.pattern[:120] for ep in pp.error_patterns[:3]
                ]
                targets.append({
                    'ptool': name,
                    'total_errors': total_errors,
                    'error_rate': total_errors / pp.n_calls if pp.n_calls else 0,
                    'top_patterns': top_patterns,
                })

        summary_parts = [
            f'{t["ptool"]} ({t["total_errors"]} errors)' for t in targets
        ]
        return TransformProposal(
            transform_name='repair',
            rationale=(
                f'Ptool(s) with errors: {", ".join(summary_parts)}. '
                f'Adding error handling to improve reliability.'
            ),
            changes=targets,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        # Build error summary for the prompt
        error_lines = ['Ptools with errors that need repair:']
        for change in proposal.changes:
            ptool_name = change['ptool']
            error_lines.append(
                f'\n  {ptool_name} ({change["total_errors"]} errors, '
                f'error_rate={change["error_rate"]:.0%}):'
            )
            for pattern in change['top_patterns']:
                error_lines.append(f'    - {pattern}')

        template = Template((_PROMPT_DIR / 'transform_base.txt').read_text())
        instruction = (
            'Add ERROR HANDLING around the ptool calls listed below. '
            'These ptools sometimes raise exceptions or return error strings '
            'starting with "**exception". For each failing ptool:\n'
            '1. Wrap the call in try/except\n'
            '2. On failure, use a sensible fallback (e.g. return a default, '
            'retry with simpler input, or skip the step)\n'
            '3. Make sure the pipeline still returns a valid output even '
            'when a ptool fails\n\n'
            + '\n'.join(error_lines)
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
            repaired = [c['ptool'] for c in proposal.changes]
            return TransformResult(
                success=True,
                new_pipeline_code=code,
                message=(
                    f'Added error handling for {", ".join(repaired)}.'
                ),
            )
        except Exception as e:
            return TransformResult(
                success=False,
                message=f'Repair failed: {e}',
            )
