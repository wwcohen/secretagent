"""Auto-generated workflow-distilled implementation for compute_nba_answer.

Tools from /tmp/induced_ptools_v4g/rulearena_nba_induced.py are inlined below.
"""

"""Induced ptools for RuleArena nba (seed=42).

Auto-generated from results/20260416.200721.nba_react_enh_train_seed42/results.jsonl.
Model: together_ai/deepseek-ai/DeepSeek-V3.
Do not edit — regenerate via generate_induced_configs.py.
"""

from secretagent.core import implement_via
from ptools_common import _REACT_STATE


@implement_via('simulate')
def _search_cba_rule_impl(context: str, focus: str) -> str:
    """
    Searches through NBA CBA context text to find relevant rules, sections, or terms based on the specified focus.

    Extracts the most relevant portions of the CBA text that match the search focus, including surrounding
    context to ensure proper interpretation. The agent should pay attention to specific article numbers,
    section headers, defined terms, and any numerical thresholds or constraints mentioned in the text.

    The response should be structured as a plain text excerpt from the CBA with clear section references,
    or as a JSON object containing 'section_reference' and 'rule_text' if the context is structured.

    Returns:
    A string containing the relevant CBA rule text with section reference. Example output:
    "Article XI, Section 4(b): A Qualifying Offer is a one-year offer of contract..."
    """


def search_cba_rule(focus: str) -> str:
    """Search the NBA Collective Bargaining Agreement for specific rules, sections, or terms.

    Args:
        focus: what aspect to reason about (e.g. a fee rule,
               a form line, a player contract, a constraint).
    """
    return _search_cba_rule_impl(_REACT_STATE["context"], focus)


@implement_via('simulate')
def _analyze_operation_compliance_impl(context: str, focus: str) -> str:
    """
    Analyzes whether a proposed NBA operation complies with Collective Bargaining Agreement rules.

    This function examines specific operations (trades, signings, offers) in the context of
    team salary caps, player contracts, and CBA regulations to identify potential violations.

    Args:
        context: A string containing relevant CBA rules, team salary situations, player
                 contract details, and the specific operation(s) to analyze.
        focus:   A string specifying the particular aspect to focus on (e.g., 'qualifying_offer',
                 'offer_sheet', 'trade_exception', 'salary_cap_threshold', 'player_contract_type').

    Returns:
        A structured string in JSON format containing:
        - compliance_status: 'compliant', 'non_compliant', or 'requires_additional_conditions'
        - rule_violations: List of specific CBA rules that would be violated (if any)
        - analysis: Detailed explanation of the compliance assessment
        - conditions: Any additional conditions required for compliance (if applicable)
        - focus_applied: The specific focus area that was analyzed

    Agent should pay attention to:
        - Current salary cap and tax apron thresholds
        - Player contract types (rookie, veteran, minimum, etc.)
        - Team salary situations (cap space, exceptions available)
        - Specific CBA rules regarding qualifying offers, offer sheets, trades
        - Year-specific salary cap amounts and exception values
        - Player service time and free agent status

    Example return:
        {
            "compliance_status": "non_compliant",
            "rule_violations": ["Article VII, Section 6(c)"],
            "analysis": "The proposed offer sheet exceeds the maximum allowed...",
            "conditions": null,
            "focus_applied": "offer_sheet"
        }
    """


def analyze_operation_compliance(focus: str) -> str:
    """Analyzes NBA CBA compliance for specific operations given team salary situations and player contracts.

    Args:
        focus: what aspect to reason about (e.g. a fee rule,
               a form line, a player contract, a constraint).
    """
    return _analyze_operation_compliance_impl(_REACT_STATE["context"], focus)


@implement_via('simulate')
def _search_cba_term_impl(context: str, focus: str) -> str:
    """
    Searches the provided NBA CBA context for a specific term, rule clause, table structure, or data point.
    This function performs a case-insensitive text search to locate relevant information based on the user's focus.
    The agent should use this to quickly find rules related to specific salary cap mechanisms (e.g., Traded Player Exception),
    contract types, cap thresholds, or specific table/formats within the CBA document.

    Args:
        context: The full text of the NBA CBA rules, team salary data, and player contract information.
        focus: The specific term, clause, table name, or data structure to search for (e.g., 'Traded Player Exception', 'apron', 'Salary Cap Year 2023').

    Returns:
        A structured string containing all context lines that match the search term, presented in order.
        Each matching line is numbered and prefixed with its position for reference.
        Returns 'No matches found.' if the search term is not present.

    Example output for focus='Traded Player Exception':
        Line 145: The Traded Player Exception allows a team to acquire a player...
        Line 146: ...up to 100% of the outgoing salary plus $100,000.
        Line 312: ...Traded Player Exception cannot be combined with other exceptions...
    """


def search_cba_term(focus: str) -> str:
    """Searches for specific terms, clauses, or structures within the NBA Collective Bargaining Agreement context.

    Args:
        focus: what aspect to reason about (e.g. a fee rule,
               a form line, a player contract, a constraint).
    """
    return _search_cba_term_impl(_REACT_STATE["context"], focus)


@implement_via('simulate')
def _search_cba_section_impl(context: str, focus: str) -> str:
    """
    Searches through NBA CBA context text to locate specific rule sections or provisions based on the agent's focus.

    This function scans the provided context text for sections, subsections, or specific rule references
    that match the agent's focus. It's designed to quickly locate relevant CBA rules when the agent knows
    exactly what section they need to reference (e.g., 'draft pick penalty', 'sign-and-trade provision',
    'section 8(e)(1)').

    Key considerations:
    - Matches exact section numbers/letters when provided (e.g., 'Section 8(e)(1)')
    - Searches for keywords in section headers when specific numbers aren't provided
    - Returns the full text of matching sections including any relevant subsections
    - Prioritizes exact matches over partial matches
    - Handles common CBA section formatting patterns

    Returns:
    A structured string containing:
    - The exact section identifier found
    - The full text of the matching section
    - Contextual information around the section if relevant
    - Empty string if no matching section is found

    Example output:
    "Section 8(e)(1): Sign-and-Trade Arrangements

    A team may sign-and-trade its own free agent provided that...

    [Additional rule text]"
    """


def search_cba_section(focus: str) -> str:
    """Searches for specific Collective Bargaining Agreement rule sections within context text.

    Args:
        focus: what aspect to reason about (e.g. a fee rule,
               a form line, a player contract, a constraint).
    """
    return _search_cba_section_impl(_REACT_STATE["context"], focus)


@implement_via('simulate')
def _search_cba_exception_impl(context: str, focus: str) -> str:
    """
    Searches the provided CBA context text for specific exception rules that match the given focus.

    Extracts and returns relevant exception details including eligibility criteria,
    calculation rules, and usage limitations. The function focuses on matching
    the specific exception type mentioned in the focus parameter against the
    context text.

    Agent should pay attention to:
    - Exception-specific salary thresholds and calculation formulas
    - Team eligibility requirements (e.g., team salary status, timing constraints)
    - Player-specific eligibility criteria
    - Stacking restrictions with other exceptions
    - Any hard constraints or limitations on exception usage

    Returns:
    A structured string containing exception details in JSON format:
    {
      "exception_found": boolean,
      "exception_name": string,
      "description": string,
      "eligibility_rules": [string],
      "calculation_method": string,
      "limitations": string
    }

    Example return:
    \"\"\"{
      "exception_found": true,
      "exception_name": "Traded Player Exception",
      "description": "Allows teams to acquire players in trades without matching salaries",
      "eligibility_rules": ["Team must be below tax apron", "Cannot combine with other exceptions"],
      "calculation_method": "125% of outgoing salary plus $100,000",
      "limitations": "Exception expires one year after creation"
    }\"\"\"
    """


def search_cba_exception(focus: str) -> str:
    """Searches for specific Collective Bargaining Agreement exceptions that could apply to a team's salary cap situation.

    Args:
        focus: what aspect to reason about (e.g. a fee rule,
               a form line, a player contract, a constraint).
    """
    return _search_cba_exception_impl(_REACT_STATE["context"], focus)


def compute_nba_answer(scenario: str, cba_text: str) -> float:
    # Initialize state just in case any underlying tool needs it
    try:
        from ptools_common import _REACT_STATE
        _REACT_STATE['narrative'] = scenario
        _REACT_STATE['cba_text'] = cba_text
    except ImportError:
        pass

    # Use implement_via to construct a direct LLM evaluator
    # Claude 3.5 Sonnet supports up to 200k tokens, which comfortably fits the ~25k token CBA text
    @implement_via('simulate', model='claude-3-5-sonnet-20241022')
    def evaluate_nba_scenario(scenario_text: str, rules_text: str) -> float:
        """
        Carefully read the NBA team situations and operations in `scenario_text`.
        Using the rules provided in `rules_text`, determine if ANY operation violates the CBA rules.
        Return 1.0 if there is at least one violation.
        Return 0.0 if there are no violations.
        """
        pass

    try:
        result = evaluate_nba_scenario(scenario, cba_text)
        
        # Parse and return the exact expected float types
        if isinstance(result, (float, int)):
            val = float(result)
            if val in [0.0, 1.0]:
                return val
                
        # Fallback string parsing
        result_str = str(result).strip()
        if result_str in ['1.0', '1']:
            return 1.0
        elif result_str in ['0.0', '0']:
            return 0.0
            
    except Exception:
        pass
        
    # Return None if the model fails or produces an unparseable response
    return None
