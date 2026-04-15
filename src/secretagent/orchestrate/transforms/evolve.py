"""Evolve transform: improve ptools via evolutionary LLM refinement."""

from __future__ import annotations

import logging
from typing import Any

from secretagent.core import Interface, all_interfaces
from secretagent.dataset import Case
from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.pipeline import Pipeline

log = logging.getLogger(__name__)


class EvolveTransform(PipelineTransform):
    """Improve individual ptools via evolutionary LLM refinement.

    Uses improve_ptool_within_workflow from experimental/improve.py to
    evolve the weakest ptool(s) identified by profiling data.

    Set workflow_interface and train_cases before calling improve_pipeline.
    """

    name = 'evolve'
    requires_llm = True

    def __init__(
        self,
        workflow_interface: Interface | None = None,
        train_cases: list[Case] | None = None,
        population_size: int = 3,
        n_generations: int = 2,
        pareto: bool = False,
    ):
        self.workflow_interface = workflow_interface
        self.train_cases = train_cases
        self.population_size = population_size
        self.n_generations = n_generations
        self.pareto = pareto
        self._profile: PipelineProfile | None = None

    def should_apply(self, profile: PipelineProfile) -> bool:
        self._profile = profile  # stash for apply() to pass to LLM
        if self.workflow_interface is None or not self.train_cases:
            log.debug('evolve: skipped (no workflow_interface or train_cases)')
            return False
        # Apply when there's room to improve
        return profile.accuracy < 1.0 and len(profile.ptool_profiles) > 0

    # Utility ptools where docstring evolution rarely helps
    SKIP_UTILITIES = {'extract_index', 'raw_answer', 'format_answer'}

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        targets = []
        for name, pp in profile.ptool_profiles.items():
            if pp.n_calls < 3 or name in self.SKIP_UTILITIES:
                continue
            error_count = sum(e.frequency for e in pp.error_patterns)
            error_rate = error_count / pp.n_calls if pp.n_calls else 0.0
            # Prefer high-cost ptools (where improvement has impact)
            score = pp.cost_fraction + error_rate * 0.5
            targets.append({
                'ptool': name,
                'weakness': score,
                'presence_in_correct': pp.presence_in_correct,
                'presence_in_incorrect': pp.presence_in_incorrect,
                'cost_fraction': pp.cost_fraction,
                'error_count': error_count,
            })

        targets.sort(key=lambda t: t['weakness'], reverse=True)
        targets = targets[:1]

        return TransformProposal(
            transform_name='evolve',
            rationale=(
                f'Evolving weakest ptool(s): '
                f'{", ".join(t["ptool"] for t in targets)}.'
            ),
            changes=targets,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        from secretagent.experimental.improve import (
            improve_ptool_within_workflow, _apply_variant, _get_ptool_info,
        )
        from secretagent.orchestrate.transforms.base import format_profiling_summary

        # Build profiling summary for the LLM (FREE)
        prof_summary = ''
        if self._profile is not None:
            prof_summary = format_profiling_summary(self._profile)

        evolved = []
        for change in proposal.changes:
            ptool_name = change['ptool']
            log.info('evolve: improving %s', ptool_name)

            try:
                result = improve_ptool_within_workflow(
                    ptool_name=ptool_name,
                    workflow_interface=self.workflow_interface,
                    train_cases=self.train_cases,
                    population_size=self.population_size,
                    n_generations=self.n_generations,
                    profiling_summary=prof_summary,
                    pareto=self.pareto,
                )
            except Exception as e:
                log.warning('evolve: failed to improve %s: %s', ptool_name, e)
                continue

            if result['improved']:
                # Apply the evolved code to the actual ptool
                ptool = _find_interface(ptool_name)
                if ptool:
                    _apply_variant(ptool, result['code'], _get_ptool_info(ptool))
                    evolved.append({
                        'ptool': ptool_name,
                        'fitness': result['fitness'],
                        'code_len': len(result['code']),
                    })
                    log.info(
                        'evolve: improved %s (accuracy=%.2f, cost=%.4f)',
                        ptool_name,
                        result['fitness']['accuracy'],
                        result['fitness']['cost'],
                    )
            else:
                log.info('evolve: no improvement found for %s', ptool_name)

        return TransformResult(
            success=bool(evolved),
            new_ptools=[{'name': e['ptool']} for e in evolved],
            message=(
                f'Evolved {len(evolved)} ptool(s): '
                f'{", ".join(e["ptool"] for e in evolved)}'
                if evolved else 'No improvements found.'
            ),
        )


def _find_interface(name: str) -> Interface | None:
    """Find an interface by name."""
    for iface in all_interfaces():
        if iface.name == name:
            return iface
    return None
