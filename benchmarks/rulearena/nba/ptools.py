"""RuleArena NBA domain: CBA salary cap compliance checking."""

import re
from pydantic import BaseModel, Field

from secretagent.core import interface, implement_via


# -- Data models --

class NbaResult(BaseModel):
    verdict: bool = Field(
        False,
        description=(
            "True if any operation violates CBA salary cap rules, "
            "False if all operations are compliant."
        ),
    )
    illegal_operation: str = Field(
        "",
        description=(
            "Letter of the first violating operation (e.g. 'A', 'B'). "
            "Empty string if no violation."
        ),
    )
    problematic_team: str = Field(
        "",
        description=(
            "Letter of the team that commits the violation (e.g. 'A', 'B'). "
            "Empty string if no violation."
        ),
    )
    reasoning: str = Field(
        "",
        description="Brief explanation of why the operation violates or complies with the rules.",
    )


# -- Constants --

_NBA_ASSUMPTIONS = (
    "Assume:\n"
    "* the Salary Cap for the prior (2023-24) Salary Cap Year is $136,000,000;\n"
    "* the Average Player Salary for the prior (2023-24) Salary Cap Year is $9,700,000;\n"
    "* the Salary Cap for the current (2024-25) NBA Salary Cap Year is $140,588,000;\n"
    "* the Luxury Tax is $170,814,000;\n"
    "* the First Apron Level is $178,132,000;\n"
    "* the Second Apron Level is $188,931,000;\n"
    "* the Team Salary of each team listed under \"Team Situations:\" do not "
    "include the amount of contracts that expire at the end of 2023-2024 Salary Cap Year.\n"
)


# -- Interfaces bound via conf.yaml --

@interface
def extract_nba_params(query: str) -> NbaResult:
    """Determine whether any NBA team operation violates CBA salary cap rules.

    Analyze the team situations, player situations, and proposed operations
    against the NBA Collective Bargaining Agreement rules provided.
    Return a structured result with verdict, the violating operation letter,
    the problematic team letter, and reasoning.
    """
    ...


@interface
def compute_nba_answer(problem_text: str, rules_text: str) -> float:
    """Given NBA team situations, player situations, proposed operations, and
    CBA salary cap rules, determine if any operation violates the rules.
    Return 1.0 if any violation exists, 0.0 if all operations are compliant.
    """
    ...


# -- Unstructured (zero-shot) helpers: always bound --

@implement_via('prompt_llm',
               prompt_template_file='prompt_templates/unstructured.txt',
               answer_pattern=None)
def zeroshot_nba(problem_text: str, rules_text: str) -> str:
    ...


def _parse_verdict_answer(llm_output: str) -> float:
    """Extract True/False verdict from an unstructured LLM response.

    Primary: <answer>True</answer> or <answer>False</answer>.
    Fallback: last standalone True/False in the text.
    Raises ValueError if no verdict found.
    """
    m = re.search(r'<answer>\s*(true|false)\s*</answer>', llm_output, re.IGNORECASE)
    if m:
        return 1.0 if m.group(1).lower() == 'true' else 0.0
    matches = re.findall(r'\b(true|false)\b', llm_output, re.IGNORECASE)
    if matches:
        return 1.0 if matches[-1].lower() == 'true' else 0.0
    raise ValueError(f"no verdict found in LLM output: {llm_output!r}")


# -- Workflows (bound via conf.yaml as direct implementations) --

def nba_workflow(problem_text: str, rules_text: str) -> float:
    """Handcoded workflow: LLM extracts structured NbaResult, return verdict."""
    query = (
        f"Reference Rules in NBA Collective Bargaining Agreement:\n\n"
        f"{rules_text}\n\n{problem_text}"
    )
    result = extract_nba_params(query=query)
    return float(result.verdict)


def unstructured_workflow(problem_text: str, rules_text: str) -> float:
    """Zero-shot unstructured workflow: prompt LLM, parse verdict."""
    raw = zeroshot_nba(problem_text=problem_text, rules_text=rules_text)
    return _parse_verdict_answer(raw)
