"""Upgrade transform: swap to a stronger model for underperforming ptools."""

from __future__ import annotations

from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.pipeline import Pipeline

# Ordered from cheapest/weakest to most expensive/strongest
_STRONG_MODELS = [
    'together_ai/google/gemma-3n-E4B-it',
    'together_ai/LiquidAI/LFM2-24B-A2B',
    'together_ai/openai/gpt-oss-20b',
    'together_ai/Qwen/Qwen3.5-9B',
    'together_ai/openai/gpt-oss-120b',
    'together_ai/essentialai/rnj-1-instruct',
    'together_ai/Qwen/Qwen3-235B-A22B-Instruct-2507-tput',
    'together_ai/MiniMaxAI/MiniMax-M2.5',
    'together_ai/moonshotai/Kimi-K2.5',
    'together_ai/Qwen/Qwen3-Coder-Next-FP8',
    'together_ai/deepseek-ai/DeepSeek-V3.1',
    'together_ai/Qwen/Qwen3.5-397B-A17B',
]


class UpgradeTransform(PipelineTransform):
    """Swap underperforming ptools to a stronger model.

    Inverse of DowngradeTransform. Triggers when a ptool has high error
    rate but low cost fraction (room in the budget for a stronger model).
    Config-only change.
    """

    name = 'upgrade'
    requires_llm = False

    def should_apply(self, profile: PipelineProfile) -> bool:
        for pp in profile.ptool_profiles.values():
            error_count = sum(e.frequency for e in pp.error_patterns)
            error_rate = error_count / pp.n_calls if pp.n_calls else 0.0
            if error_rate > 0.3 and pp.cost_fraction < 0.3:
                return True
        return False

    def propose(
        self, profile: PipelineProfile, catalog: PtoolCatalog,
    ) -> TransformProposal:
        targets = []
        for name, pp in profile.ptool_profiles.items():
            error_count = sum(e.frequency for e in pp.error_patterns)
            error_rate = error_count / pp.n_calls if pp.n_calls else 0.0
            if error_rate > 0.3 and pp.cost_fraction < 0.3:
                targets.append({
                    'ptool': name,
                    'error_rate': error_rate,
                    'cost_fraction': pp.cost_fraction,
                })

        targets.sort(key=lambda t: t['error_rate'], reverse=True)
        return TransformProposal(
            transform_name='upgrade',
            rationale=(
                f'Upgrading ptools with high error rates and low cost: '
                f'{", ".join(t["ptool"] for t in targets)}'
            ),
            changes=targets,
        )

    def apply(
        self,
        proposal: TransformProposal,
        pipeline: Pipeline,
        catalog: PtoolCatalog,
    ) -> TransformResult:
        from secretagent import config

        current_model = config.get('llm.model', '')

        # Find current model's position
        current_idx = -1
        for i, m in enumerate(_STRONG_MODELS):
            if m == current_model or current_model.endswith(m.split('/')[-1]):
                current_idx = i
                break

        # Pick the next stronger model
        stronger = None
        for m in _STRONG_MODELS[current_idx + 1:]:
            stronger = m
            break  # take the next one up

        if stronger is None:
            return TransformResult(
                success=False,
                message=f'Already using strongest available model ({current_model}).',
            )

        new_config: dict = {}
        upgraded = []
        for change in proposal.changes:
            ptool_name = change['ptool']
            new_config[f'ptools.{ptool_name}.model'] = stronger
            upgraded.append(ptool_name)

        return TransformResult(
            success=True,
            new_config=new_config,
            message=f'Upgraded {", ".join(upgraded)} from {current_model} to {stronger}.',
        )
