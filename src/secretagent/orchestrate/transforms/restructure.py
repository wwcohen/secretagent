"""Restructure transform: reorganize the overall pipeline flow."""

from __future__ import annotations

from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.pipeline import Pipeline


class RestructureTransform(PipelineTransform):
    """Reorganize the pipeline's control flow and tool call ordering.

    Implementation guide:
    Use the profiling data to identify whether reordering steps,
    adding early exits, or restructuring conditionals could improve
    accuracy or reduce cost. Generate a restructured pipeline via LLM.
    """

    name = 'restructure'
    requires_llm = True

    def should_apply(self, profile: PipelineProfile) -> bool:
        return True  # restructuring is always worth considering

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        raise NotImplementedError('TODO: implement restructure transform')

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        raise NotImplementedError('TODO: implement restructure transform')
