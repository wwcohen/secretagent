"""Swap strategy transform: change implementation method for a ptool."""

from __future__ import annotations

from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.pipeline import Pipeline


# Available implementation methods and their characteristics
_METHODS = {
    'simulate': {'cost': 'medium', 'accuracy': 'medium', 'needs_llm': True},
    'prompt_llm': {'cost': 'medium', 'accuracy': 'high', 'needs_llm': True},
    'program_of_thought': {'cost': 'high', 'accuracy': 'high', 'needs_llm': True},
    'direct': {'cost': 'zero', 'accuracy': 'variable', 'needs_llm': False},
}

# Upgrade paths when accuracy is the problem
_ACCURACY_UPGRADES = {
    'simulate': ['prompt_llm', 'program_of_thought'],
    'prompt_llm': ['program_of_thought'],
}

# Downgrade paths when cost is the problem
_COST_DOWNGRADES = {
    'program_of_thought': ['prompt_llm', 'simulate'],
    'prompt_llm': ['simulate'],
    'simulate': ['direct'],
}


class SwapStrategyTransform(PipelineTransform):
    """Change implementation method for underperforming or expensive ptools.

    Triggers:
    - error_rate > 0.2: ptool has too many errors → try different method
    - cost_fraction > 0.5: ptool consumes too much cost → try cheaper method
    - output_token_saturation > 0.9: ptool hitting token limit → increase max_tokens

    This is a config-only transform (no LLM needed).
    """

    name = 'swap_strategy'
    requires_llm = False

    def should_apply(self, profile: PipelineProfile) -> bool:
        for pp in profile.ptool_profiles.values():
            error_count = sum(e.frequency for e in pp.error_patterns)
            error_rate = error_count / pp.n_calls if pp.n_calls else 0.0
            if error_rate > 0.2:
                return True
            if pp.cost_fraction > 0.5:
                return True
            if pp.output_token_saturation > 0.9:
                return True
        return False

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        targets = []
        for name, pp in profile.ptool_profiles.items():
            error_count = sum(e.frequency for e in pp.error_patterns)
            error_rate = error_count / pp.n_calls if pp.n_calls else 0.0
            reason = None

            if error_rate > 0.2:
                reason = f'high error rate ({error_rate:.0%})'
            elif pp.cost_fraction > 0.5:
                reason = f'high cost fraction ({pp.cost_fraction:.0%})'
            elif pp.output_token_saturation > 0.9:
                reason = f'token saturation ({pp.output_token_saturation:.0%})'

            if reason:
                targets.append({
                    'ptool': name,
                    'reason': reason,
                    'error_rate': error_rate,
                    'cost_fraction': pp.cost_fraction,
                    'token_saturation': pp.output_token_saturation,
                })

        descriptions = ', '.join(
            f'{t["ptool"]} ({t["reason"]})' for t in targets
        )
        return TransformProposal(
            transform_name='swap_strategy',
            rationale=f'Strategy swap targets: {descriptions}',
            changes=targets,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        from secretagent import config

        new_config: dict = {}
        swapped = []

        for change in proposal.changes:
            ptool_name = change['ptool']
            current_method = config.get(f'ptools.{ptool_name}.method', 'simulate')

            # Token saturation → increase max_tokens
            if change.get('token_saturation', 0) > 0.9:
                current_max = config.get(f'ptools.{ptool_name}.max_tokens') or config.get('llm.max_tokens', 16384)
                new_max = min(current_max * 2, 131072)
                if new_max > current_max:
                    new_config[f'ptools.{ptool_name}.max_tokens'] = new_max
                    swapped.append(f'{ptool_name}: max_tokens {current_max}→{new_max}')
                    continue

            # High error rate → try more capable method
            if change.get('error_rate', 0) > 0.2:
                upgrades = _ACCURACY_UPGRADES.get(current_method, [])
                if upgrades:
                    new_method = upgrades[0]
                    new_config[f'ptools.{ptool_name}.method'] = new_method
                    swapped.append(f'{ptool_name}: {current_method}→{new_method}')
                    continue

            # High cost → try cheaper method
            if change.get('cost_fraction', 0) > 0.5:
                downgrades = _COST_DOWNGRADES.get(current_method, [])
                if downgrades:
                    new_method = downgrades[0]
                    new_config[f'ptools.{ptool_name}.method'] = new_method
                    swapped.append(f'{ptool_name}: {current_method}→{new_method}')
                    continue

        if not swapped:
            return TransformResult(
                success=False,
                message='No viable strategy swaps found.',
            )

        return TransformResult(
            success=True,
            new_config=new_config,
            message=f'Swapped strategies: {"; ".join(swapped)}',
        )
