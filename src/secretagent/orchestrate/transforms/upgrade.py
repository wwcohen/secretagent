"""Upgrade transform: swap to a stronger model for underperforming ptools."""

from __future__ import annotations

import pathlib

from secretagent.orchestrate.catalog import PtoolCatalog
from secretagent.orchestrate.profiler import PipelineProfile
from secretagent.orchestrate.transforms.base import (
    PipelineTransform, TransformProposal, TransformResult,
)
from secretagent.orchestrate.pipeline import Pipeline


def _load_model_list() -> list[str]:
    """Load model list from models.yaml, ordered weakest to strongest."""
    models_file = pathlib.Path(__file__).resolve().parent.parent / 'models.yaml'
    if models_file.exists():
        from secretagent.config import load_yaml_cfg
        cfg = load_yaml_cfg(models_file)
        # models.yaml is ordered strongest-first; reverse for upgrade ordering
        return [m['api_string'] for m in reversed(cfg.get('models', []))
                if m.get('tier') != 'reasoning']
    # Fallback if file missing
    return [
        'together_ai/openai/gpt-oss-20b',
        'together_ai/Qwen/Qwen3.5-9B',
        'together_ai/openai/gpt-oss-120b',
        'together_ai/Qwen/Qwen3-235B-A22B-Instruct-2507-tput',
        'together_ai/MiniMaxAI/MiniMax-M2.5',
        'together_ai/deepseek-ai/DeepSeek-V3.1',
        'together_ai/Qwen/Qwen3.5-397B-A17B',
        'together_ai/MiniMaxAI/MiniMax-M2.7',
        'together_ai/zai-org/GLM-5.1',
    ]


_STRONG_MODELS = _load_model_list()


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

        # Find current model's position in ranked model list
        current_idx = None
        for i, m in enumerate(_STRONG_MODELS):
            if m == current_model or current_model.endswith(m.split('/')[-1]):
                current_idx = i
                break

        if current_idx is None:
            # Unknown model — upgrade to strongest available
            stronger = _STRONG_MODELS[-1]
        else:
            # Pick the next stronger model
            stronger = None
            for m in _STRONG_MODELS[current_idx + 1:]:
                stronger = m
                break

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
