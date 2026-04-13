"""Crossover transform: combine subflows from two pipeline variants."""

from __future__ import annotations

import logging
import pathlib
from string import Template

from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.pipeline import Pipeline

log = logging.getLogger(__name__)

_PROMPT_DIR = pathlib.Path(__file__).resolve().parent.parent / 'prompt_templates'


class CrossoverTransform(PipelineTransform):
    """Combine subflows from two pipeline variants.

    Requires population_size > 1. Selects two Pareto-front candidates
    with complementary strengths and asks LLM to merge them.

    Set `other_candidate` before calling apply().
    """

    name = 'crossover'
    requires_llm = True

    def __init__(self):
        self.other_candidate = None  # set externally by population mode
        self._other_pipeline: Pipeline | None = None
        self._other_profile: PipelineProfile | None = None

    def set_other(self, pipeline: Pipeline, profile: PipelineProfile | None = None) -> None:
        """Set the second parent for crossover."""
        self._other_pipeline = pipeline
        self._other_profile = profile

    def should_apply(self, profile: PipelineProfile) -> bool:
        return self._other_pipeline is not None

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        other_acc = self._other_profile.accuracy if self._other_profile else 0.0
        return TransformProposal(
            transform_name='crossover',
            rationale=(
                f'Crossing parent A (accuracy={profile.accuracy:.1%}) '
                f'with parent B (accuracy={other_acc:.1%})'
            ),
            changes=[{
                'parent_a_accuracy': profile.accuracy,
                'parent_a_cost': profile.avg_cost,
                'parent_b_accuracy': other_acc,
                'parent_b_cost': self._other_profile.avg_cost if self._other_profile else 0.0,
            }],
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        if self._other_pipeline is None:
            return TransformResult(
                success=False,
                message='No second parent set for crossover.',
            )

        template_path = _PROMPT_DIR / 'crossover.txt'
        if not template_path.exists():
            return TransformResult(
                success=False,
                message='crossover.txt template not found.',
            )

        template = Template(template_path.read_text())
        other_acc = self._other_profile.accuracy if self._other_profile else 0.0
        other_cost = self._other_profile.avg_cost if self._other_profile else 0.0

        prompt = template.substitute(
            parent_a_index=0,
            parent_a_accuracy=f'{proposal.changes[0].get("parent_a_accuracy", 0):.1%}',
            parent_a_cost=f'${proposal.changes[0].get("parent_a_cost", 0):.4f}',
            parent_a_code=pipeline.source,
            parent_b_index=1,
            parent_b_accuracy=f'{other_acc:.1%}',
            parent_b_cost=f'${other_cost:.4f}',
            parent_b_code=self._other_pipeline.source,
            tool_stubs=catalog.render(),
            entry_signature=pipeline.entry_signature,
        )

        try:
            code = self._generate_code(prompt, pipeline.entry_signature)
            self._validate_code(
                code, pipeline.entry_signature, pipeline._fn.__globals__,
            )
            return TransformResult(
                success=True,
                new_pipeline_code=code,
                message='Crossed over two parent pipelines.',
            )
        except Exception as e:
            return TransformResult(
                success=False,
                message=f'Crossover failed: {e}',
            )
