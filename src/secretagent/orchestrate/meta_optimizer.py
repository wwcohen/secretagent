"""Meta-optimizer: LLM-guided mutation operator selection."""

from __future__ import annotations

import json
import logging
import pathlib
from string import Template
from typing import Any

from pydantic import BaseModel

from secretagent import config
from secretagent.llm_util import llm

log = logging.getLogger(__name__)

_PROMPT_DIR = pathlib.Path(__file__).resolve().parent / 'prompt_templates'


def _extract_json_array(text: str) -> str | None:
    """Extract a JSON array from text using bracket-balancing."""
    start = text.find('[')
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


class MutationProposal(BaseModel):
    """A single mutation proposed by the meta-optimizer."""
    operator: str
    candidate_index: int
    reasoning: str
    params: dict[str, Any] = {}


class MetaOptimizer:
    """Uses a big LLM to reason about which mutation operators to apply.

    The meta-optimizer sees the population summary, profiling data, and
    available operators, then proposes 1-3 mutations per iteration.
    """

    def __init__(
        self,
        model: str | None = None,
        operators: dict[str, Any] | None = None,
    ):
        self.model = model or config.get(
            'improve.meta_model',
            'together_ai/deepseek-ai/DeepSeek-V3.1',
        )
        self.operators = operators or {}

    def guide(
        self,
        population_summary: str,
        profiling_details: str,
        operator_descriptions: str,
        budget_summary: dict,
    ) -> tuple[list[MutationProposal], float]:
        """Ask the LLM which mutations to apply.

        Returns:
            (proposals, cost) — list of MutationProposal and the LLM call cost
        """
        template_path = _PROMPT_DIR / 'meta_guide.txt'
        if not template_path.exists():
            log.warning('meta_guide.txt not found, returning empty proposals')
            return [], 0.0

        template = Template(template_path.read_text())
        total_spent = budget_summary.get('total_spent', 0)
        budget_limit = budget_summary.get('budget_limit', 0)
        prompt = template.substitute(
            n_candidates=budget_summary.get('n_candidates', '?'),
            generation=budget_summary.get('generation', '?'),
            population_summary=population_summary,
            operator_descriptions=operator_descriptions,
            profiling_details=profiling_details,
            spent_display=f"${total_spent:.2f}",
            budget_display=f"${budget_limit:.2f}" if budget_limit < float('inf') else "unlimited",
            pct_spent=f"{budget_summary.get('pct_spent', 0):.0f}",
            budget_mode=budget_summary.get('mode', 'soft_stop'),
        )

        text, stats = llm(prompt, self.model)
        cost = stats.get('cost', 0.0)

        proposals = self._parse_proposals(text)
        log.info('meta-optimizer proposed %d mutations (cost=$%.4f)', len(proposals), cost)
        return proposals, cost

    def _parse_proposals(self, text: str) -> list[MutationProposal]:
        """Extract JSON array of mutation proposals from LLM output."""
        json_str = _extract_json_array(text)
        if not json_str:
            log.warning('meta-optimizer: no JSON array found in response')
            return []

        try:
            raw = json.loads(json_str)
        except json.JSONDecodeError:
            log.warning('meta-optimizer: failed to parse JSON from response')
            return []

        if not isinstance(raw, list):
            return []

        proposals = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                proposals.append(MutationProposal(
                    operator=item.get('operator', ''),
                    candidate_index=int(item.get('candidate_index', 0)),
                    reasoning=item.get('reasoning', ''),
                    params=item.get('params', {}),
                ))
            except (ValueError, TypeError) as e:
                log.warning('meta-optimizer: skipping malformed proposal: %s', e)
                continue

        # Filter to known operators
        if self.operators:
            known = set(self.operators.keys())
            valid = [p for p in proposals if p.operator in known]
            if len(valid) < len(proposals):
                skipped = [p.operator for p in proposals if p.operator not in known]
                log.warning('meta-optimizer: skipped unknown operators: %s', skipped)
            proposals = valid

        return proposals
