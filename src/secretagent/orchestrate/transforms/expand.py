"""Expand transform: decompose underperforming ptools into sub-steps."""

from __future__ import annotations

from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.pipeline import Pipeline


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
            pp.cost_fraction > 0.3 and pp.presence_in_correct < profile.accuracy * 0.8
            for pp in profile.ptool_profiles.values()
        )

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        raise NotImplementedError('TODO: implement expand transform')

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        raise NotImplementedError('TODO: implement expand transform')
