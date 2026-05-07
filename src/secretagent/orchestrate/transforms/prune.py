"""Prune transform: remove ptools that contribute negligible accuracy lift."""

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


class PruneTransform(PipelineTransform):
    """Remove ptools whose accuracy lift is negligible.

    Identifies ptools with lift < 0.02 (they add cost but barely help
    accuracy) and asks an LLM to rewrite the pipeline without them.
    """

    name = 'prune'
    requires_llm = True

    def should_apply(self, profile: PipelineProfile) -> bool:
        return any(
            pp.lift is not None and pp.lift < 0.02
            for pp in profile.ptool_profiles.values()
        )

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        targets = []
        for name, pp in profile.ptool_profiles.items():
            if pp.lift is not None and pp.lift < 0.02:
                targets.append({
                    'ptool': name,
                    'lift': pp.lift,
                    'cost_fraction': pp.cost_fraction,
                })

        return TransformProposal(
            transform_name='prune',
            rationale=(
                f'Ptool(s) with negligible lift (<0.02): '
                f'{", ".join(t["ptool"] for t in targets)}. '
                f'Removing them saves '
                f'{sum(t["cost_fraction"] for t in targets):.0%} of cost.'
            ),
            changes=targets,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        prune_names = [c['ptool'] for c in proposal.changes]

        template = Template((_PROMPT_DIR / 'transform_base.txt').read_text())
        instruction = (
            f'REMOVE all calls to these ptools: {", ".join(prune_names)}. '
            f'They have negligible accuracy lift and just waste cost. '
            f'Rewrite the function body so it produces the same output '
            f'WITHOUT calling those ptools. You may need to restructure '
            f'the logic — for example, if a pruned ptool produced an '
            f'intermediate value, replace it with a reasonable default '
            f'or skip the step entirely.'
        )

        # Build a summary of just the pruned ptools
        summary_lines = ['Ptools to REMOVE (negligible lift):']
        for c in proposal.changes:
            summary_lines.append(
                f'  {c["ptool"]}: lift={c["lift"]:.3f}, '
                f'cost_fraction={c["cost_fraction"]:.1%}'
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
            return TransformResult(
                success=True,
                new_pipeline_code=code,
                message=f'Pruned {", ".join(prune_names)} from pipeline.',
            )
        except Exception as e:
            return TransformResult(
                success=False,
                message=f'Prune failed: {e}',
            )
