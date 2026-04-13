"""Route transform: add conditional dispatch by input category."""

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


class RouteTransform(PipelineTransform):
    """Add conditional dispatch based on input characteristics.

    Triggers when accuracy variance across cases is high, suggesting
    different input types need different handling strategies.
    Uses LLM to analyze failure patterns and rewrite pipeline with
    conditional routing.
    """

    name = 'route'
    requires_llm = True

    def __init__(self):
        self._profile: PipelineProfile | None = None

    def should_apply(self, profile: PipelineProfile) -> bool:
        self._profile = profile  # stash for apply()
        # Check if there's meaningful variance suggesting routing would help.
        # Heuristic: if we have errors in some ptools but not others,
        # or accuracy is moderate (not very high or very low).
        if profile.accuracy > 0.95 or profile.accuracy < 0.1:
            return False
        # Need enough cases to detect patterns
        if profile.n_cases < 10:
            return False
        # Check for error variance across ptools
        error_rates = []
        for pp in profile.ptool_profiles.values():
            if pp.n_calls > 0:
                err_count = sum(e.frequency for e in pp.error_patterns)
                error_rates.append(err_count / pp.n_calls)
        if not error_rates:
            return False
        # High variance in error rates suggests routing could help
        mean_err = sum(error_rates) / len(error_rates)
        variance = sum((r - mean_err) ** 2 for r in error_rates) / len(error_rates)
        return variance > 0.01 or (0.3 < profile.accuracy < 0.85)

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        # Identify ptools with mixed success/failure patterns
        targets = []
        for name, pp in profile.ptool_profiles.items():
            if pp.accuracy_when_correct > 0 and pp.accuracy_when_incorrect > 0:
                gap = abs(pp.accuracy_when_correct - pp.accuracy_when_incorrect)
                if gap > 0.1:
                    targets.append({
                        'ptool': name,
                        'correct_rate': pp.accuracy_when_correct,
                        'incorrect_rate': pp.accuracy_when_incorrect,
                        'gap': gap,
                    })

        return TransformProposal(
            transform_name='route',
            rationale=(
                f'Accuracy variance suggests routing could help. '
                f'Overall accuracy: {profile.accuracy:.1%}. '
                f'Ptools with correctness gaps: '
                f'{", ".join(t["ptool"] for t in targets) or "general pattern"}'
            ),
            changes=targets,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        template = Template((_PROMPT_DIR / 'transform_base.txt').read_text())

        instruction = (
            'ADD CONDITIONAL ROUTING to this pipeline.\n\n'
            'The pipeline currently treats all inputs the same, but profiling '
            'shows that different input types have different success rates.\n\n'
            'Your task:\n'
            '1. Analyze the input (from function arguments) to determine its category/type\n'
            '2. Route to different tool sequences based on input characteristics\n'
            '3. Use if/elif/else to dispatch to the appropriate strategy\n'
            '4. Keep the original approach as a fallback for unrecognized inputs\n'
            '5. Each route should use the tools most effective for that input type\n\n'
            f'Profiling shows accuracy of {proposal.rationale}'
        )

        real_profile = self._profile or PipelineProfile(accuracy=0.0, ptool_profiles={})
        prompt = template.substitute(
            pipeline_code=pipeline.source,
            profiling_summary=format_profiling_summary(real_profile),
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
                message='Added conditional routing based on input characteristics.',
            )
        except Exception as e:
            return TransformResult(
                success=False,
                message=f'Route transform failed: {e}',
            )
