"""Induced ptools for answer_question."""

from secretagent.core import implement_via
from ptools_common import _REACT_STATE


@implement_via('simulate')
def _search_specific_information_impl(context: str, focus: str) -> str:
    """
    This function searches for specific information within a given context based on a focused query. It is designed to extract detailed information about particular aspects such as skills, relationships, constraints, synergies, or conflicts mentioned in the context.

    Args:
        context (str): The full problem text, narrative, or prompt containing the information to search through.
        focus (str): The specific aspect to search for (e.g., a person's name, a role, a constraint type).

    Returns:
        str: A structured string containing the extracted information. The string should be formatted with clear sections and bullet points for readability. If no information is found, return 'No specific information found.'

    Example:
        Returns:
            "Information about John Doe:
    - Skills: Python, Data Analysis
    - Relationships: Works well with Alice
    - Constraints: Not available on weekends
    - Synergies: Strong with Team A
    - Conflicts: Avoids working with Bob"
    """


def search_specific_information(focus: str) -> str:
    """Searches for specific details within a given context based on a focused query."""
    return _search_specific_information_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _final_team_selection_impl(context: str, focus: str) -> str:
    """
    Evaluates all candidate team compositions and selects the optimal allocation.
    Extracts role requirements, hard constraints (must-haves), soft constraints (preferences), 
    synergies (positive interactions), and conflicts (negative interactions) from the context.
    Focuses on the specific aspect provided (e.g., a particular role, constraint, or candidate team).
    The response should be structured as a ranked list of team allocations with justifications,
    or a single best choice if one clearly dominates. Pay attention to satisfying hard constraints
    first, then optimizing soft constraints and synergies while avoiding conflicts.

    Returns:
        str: A structured string showing the final selection. Example: "Best allocation: Team A

    Justification:
    - Satisfies all hard constraints: [constraints]
    - Maximizes soft constraints: [preferences]
    - Leverages synergies: [synergies]
    - Avoids conflicts: [conflicts]"
    """


def final_team_selection(focus: str) -> str:
    """Makes the final team allocation decision based on role requirements, constraints, synergies, and conflicts."""
    return _final_team_selection_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _define_team_allocation_problem_impl(context: str, focus: str) -> str:
    """
    Defines the structure of a team allocation problem by extracting key elements from the context.

    Extracts information about:
    - Required roles/tasks to be allocated
    - Available team members/people
    - Hard constraints (must-follow rules)
    - Soft constraints (preferences/guidelines)
    - Synergies and conflicts between team members
    - Efficiency criteria or optimization goals
    - Any specific allocation requirements mentioned

    Response should be structured as:
    1. Problem statement summary
    2. Key components identified
    3. Constraints and requirements
    4. Optimization criteria

    Pay attention to:
    - Distinguishing between hard vs. soft constraints
    - Identifying all relevant roles and people
    - Noting any explicit efficiency requirements
    - Capturing any mentioned preferences or conflicts

    Returns:
    A structured string like:
    "Problem: Allocate roles to team members efficiently

    Roles: [role1, role2]
    People: [person1, person2, person3]
    Hard Constraints: [constraint1, constraint2]
    Soft Constraints: [preference1, preference2]
    Synergies/Conflicts: [synergy/conflict details]
    Efficiency Criteria: [criteria description]"
    """


def define_team_allocation_problem(focus: str) -> str:
    """Analyzes a team allocation problem by identifying key components like roles, constraints, and personnel attributes."""
    return _define_team_allocation_problem_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _summarize_evidence_findings_impl(context: str, focus: str) -> str:
    """
    Summarizes evidence findings from the context to support team allocation decisions.

    Extracts and organizes information about each team member's skills, preferences,
    constraints (hard/soft), synergies, and conflicts. The summary should highlight
    key strengths/weaknesses for relevant roles and note critical constraints that
    must be considered.

    Structure the response with:
    1. Bullet points for each person with key findings
    2. Key insights/constraints that emerge
    3. Brief analysis of how this affects allocation options

    Pay attention to:
    - Hard constraints (must/must-not assignments)
    - Soft constraints (preferences/avoidances)
    - Skill mismatches (people bad at certain roles)
    - Interpersonal conflicts or synergies
    - Role requirements from the problem

    Returns:
    A structured string summary ready for final allocation decision-making.

    Example output:
    \"\"\"
    1. **PersonA**: 
       - Excellent at violin (won competitions)
       - Poor at percussion (struggles with rhythm)
       - Conflicts with PersonC

    2. **PersonB**:
       - Good at guitar (quick learner)
       - Prefers customer-facing roles
       - Collaborates well with PersonD

    Key insights:
    - PersonA should avoid percussion due to poor performance
    - PersonB and PersonD work well together
    - Avoid pairing PersonA and PersonC due to conflict

    Looking at the choices:
    Option 1: Violin: PersonA, Guitar: PersonB...\"\"\"
    """


def summarize_evidence_findings(focus: str) -> str:
    """Summarizes evidence findings about team members' strengths, weaknesses, constraints, and relationships to inform optimal allocation."""
    return _summarize_evidence_findings_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _analyze_constraints_and_options_impl(context: str, focus: str) -> str:
    """
    Analyzes a team allocation context to identify available options, hard constraints, soft constraints, synergies, and conflicts.

    Extracts information about:
    - Available roles/tasks and their specific requirements
    - Available team members and their attributes (skills, preferences, limitations)
    - Hard constraints (must/must-not assignments, capacity limits)
    - Soft constraints (preferences, efficiencies, strengths)
    - Synergies (positive interactions between specific members)
    - Conflicts (negative interactions between specific members)

    Structures the response by first listing all options, then detailing constraints and preferences that affect these options.

    Pay attention to:
    - Keywords indicating requirements ('must', 'should', 'expert', 'prefers')
    - Quantitative and qualitative descriptions of abilities
    - Explicit constraints ('cannot work with', 'must be assigned to')
    - Implicit constraints from narrative context
    - Task capacity requirements (e.g., 'both tasks' implies exactly one allocation per task)

    Returns: 
    A structured string with sections for Options, Hard Constraints, Soft Constraints, Synergies, and Conflicts.

    Example output:
    "Options:
    - Roles: [Task1, Task2]
    - Team: [PersonA, PersonB, PersonC]

    Hard Constraints:
    - PersonA must be assigned to Task1
    - PersonC cannot work with PersonB

    Soft Constraints:
    - PersonB excels at Task2
    - PersonC prefers Task1

    Synergies:
    - PersonA and PersonB work well together

    Conflicts:
    - PersonB and PersonC have conflicts"
    """


def analyze_constraints_and_options(focus: str) -> str:
    """Extract and evaluate role requirements, constraints, and preferences from a team allocation problem."""
    return _analyze_constraints_and_options_impl(_REACT_STATE["narrative"], focus)


