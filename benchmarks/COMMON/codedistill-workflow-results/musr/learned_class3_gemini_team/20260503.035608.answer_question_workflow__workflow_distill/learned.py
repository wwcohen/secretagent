"""Auto-generated workflow-distilled implementation for answer_question_workflow.

Tools from /tmp/induced_ptools_v4g/musr_team_induced.py are inlined below.
"""

"""Induced ptools for MUSR team (seed=42).

Auto-generated from results/20260411.041616.team_react_train_seed42/results.jsonl.
Model: together_ai/deepseek-ai/DeepSeek-V3.
Do not edit — regenerate via generate_induced_configs.py.
"""

from secretagent.core import implement_via
from ptools_common import _REACT_STATE


@implement_via('simulate')
def _analyze_and_summarize_attributes_impl(narrative: str, focus: str) -> str:
    """
    This function extracts and summarizes key attributes from a narrative text to aid in team allocation decisions.
    It focuses on identifying each person's skills, weaknesses, and interpersonal dynamics (e.g., who works well together or has conflicts).
    The summary should be structured as a clear text overview, highlighting information relevant to the specified focus (e.g., a person, role, or constraint).
    Pay special attention to hard disqualifiers (e.g., severe weaknesses for a task), tricky trade-offs, and implicit dynamics that might not be explicitly stated.
    Returns: A structured plain text summary, formatted with bullet points or numbered lists for clarity.
    Example output:
    Based on the narrative analysis:
    - **PersonA**: Skilled in X, but weak in Y. Works well with PersonB.
    - **PersonB**: Excellent at Z, but struggles with W. Conflicts with PersonC.
    """


def analyze_and_summarize_attributes(focus: str) -> str:
    """Analyzes a narrative to summarize people's strengths, weaknesses, and interpersonal dynamics relevant to task allocation.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _analyze_and_summarize_attributes_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _seek_specific_individual_information_impl(narrative: str, focus: str) -> str:
    """
    This tool extracts detailed information about specific individuals mentioned in a team allocation narrative.

    It focuses on identifying:
    - Individual strengths, skills, and specializations
    - Weaknesses, limitations, and disqualifiers
    - Personality traits and interpersonal dynamics
    - Specific constraints or preferences mentioned

    The tool returns a structured JSON object containing individuals' information organized by person. Each person entry includes their strengths, weaknesses, and other relevant characteristics mentioned in the narrative.

    Key considerations:
    - Pay attention to explicit statements about capabilities/limitations
    - Note comparative language (e.g., \"best at\", \"struggles with\")
    - Watch for interpersonal conflicts or compatibility issues
    - Identify hard constraints that might disqualify someone from certain roles

    Returns:
    {
      \"individuals\": {
        \"person_name\": {
          \"strengths\": [\"skill1\", \"skill2\", ...],
          \"weaknesses\": [\"limitation1\", \"limitation2\", ...],
          \"characteristics\": [\"trait1\", \trait2\", ...],
          \"constraints\": [\"constraint1\", \constraint2\", ...]
        },
        ...
      }
    }
    """


def seek_specific_individual_information(focus: str) -> str:
    """Extracts detailed information about specific individuals' characteristics from a narrative.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _seek_specific_individual_information_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _define_task_requirements_impl(narrative: str, focus: str) -> str:
    """
    Extracts and structures task requirements, objectives, and constraints from a team allocation narrative.

    This function analyzes the narrative to identify:
    - Specific tasks/roles mentioned
    - Required skills, strengths or qualifications for each task
    - Constraints or limitations (time, resources, interpersonal dynamics)
    - Explicit or implicit objectives/goals
    - Any disqualifying conditions or hard requirements

    Returns:
    A JSON-shaped string containing:
    {
      "tasks": [{"name": "task_name", "requirements": ["req1", "req2"], "constraints": [...]}],
      "objectives": ["primary_goal1", "secondary_goal2"],
      "constraints": {"hard": [...], "soft": [...]},
      "focus_analysis": "how the specified focus relates to requirements"
    }

    Pay special attention to:
    - Hard disqualifiers (e.g., "cannot work nights", "no legal experience")
    - Interpersonal dynamics that might affect performance
    - Implicit requirements not explicitly stated
    - Resource or time constraints that limit allocation options
    - Multiple competing objectives that need prioritization

    Example Returns:
    {"tasks": [{"name": "PR Specialist", "requirements": ["communication skills", "media relations"], "constraints": []}], "objectives": ["maximize team harmony", "complete project on time"], "constraints": {"hard": ["must have legal background"], "soft": []}, "focus_analysis": "Legal Advisor role requires specific legal expertise"}
    """


def define_task_requirements(focus: str) -> str:
    """Analyzes narrative to extract task requirements, objectives, and constraints for team allocation.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _define_task_requirements_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _analyze_team_allocation_impl(narrative: str, focus: str) -> str:
    """
    Analyzes a narrative about team members' characteristics to extract key information for task allocation.

    Extracts information about each person's:
    - Strengths/skills relevant to tasks
    - Weaknesses/limitations to avoid
    - Interpersonal dynamics (conflicts, synergies)
    - Any explicit preferences or constraints

    Returns a structured JSON string with:
    {
      "people": [
        {
          "name": "person_name",
          "strengths": ["skill1", "skill2", ...],
          "weaknesses": ["limitation1", ...],
          "relationships": {"person_name": "dynamic_description", ...}
        }
      ],
      "tasks": ["task1_description", "task2_description", ...],
      "constraints": ["constraint1", ...]
    }

    Pay attention to:
    - Implicit skills that might be inferred from descriptions
    - Hard disqualifiers (e.g., "cannot work with X")
    - Relative strength comparisons between team members
    - Any time or resource constraints mentioned

    Example Returns:
    '{"people": [{"name": "Maria", "strengths": ["analytical", "organized"], "weaknesses": ["public speaking"], "relationships": {"Jake": "works well with"}}], "tasks": ["data analysis", "client presentation"], "constraints": ["must complete within 2 days"]}'
    """


def analyze_team_allocation(focus: str) -> str:
    """Analyzes narrative about team members' skills and dynamics to determine optimal task assignments.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _analyze_team_allocation_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _make_final_allocation_decision_impl(narrative: str, focus: str) -> str:
    """
    Analyzes the narrative to identify available assignment options and selects the best one based on:
    - Team member strengths, weaknesses, and interpersonal dynamics
    - Task requirements and constraints
    - Overall team composition effectiveness

    Focus parameter can specify a particular constraint to prioritize (e.g., 'conflict_avoidance', 'skill_match', 'efficiency').

    Returns a single integer representing the index (0-indexed) of the chosen assignment option.

    Example return: '2' (indicating selection of the third assignment option)

    Note: The function assumes the narrative implicitly or explicitly presents multiple assignment alternatives
    that need to be evaluated and ranked. Pay special attention to disqualifying constraints (e.g., conflicts,
    skill gaps, role incompatibilities) that might eliminate certain options entirely.
    """


def make_final_allocation_decision(focus: str) -> str:
    """Selects the optimal team assignment option based on narrative constraints and requirements.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _make_final_allocation_decision_impl(_REACT_STATE["narrative"], focus)


def answer_question_workflow(narrative, question, choices):
    """
    Solves the team allocation task end-to-end by orchestrating the provided analysis tools.
    """
    import re
    
    # CRITICAL: Initialize module-level state for tools that read it
    try:
        from ptools_common import _REACT_STATE
        _REACT_STATE['narrative'] = narrative
    except ImportError:
        pass

    try:
        # Step 1: Gather team attributes, strengths, and weaknesses
        attributes_summary = analyze_and_summarize_attributes("Identify strengths, weaknesses, and interpersonal dynamics.")
        if not attributes_summary:
            attributes_summary = "No explicit attribute summary available."

        # Step 2: Formulate the prompt for the final decision tool
        focus_text = f"""Task Question: {question}

Available Choices:
0: {choices[0]}
1: {choices[1]}
2: {choices[2]}

Narrative Context:
{narrative}

Team Attributes Analysis:
{attributes_summary}

Task: Based on the narrative constraints and team dynamics, evaluate which assignment choice is optimal. 
You MUST return ONLY the single integer index (0, 1, or 2) of the correct choice. Do not provide any explanation.
"""

        # Step 3: Call the decision tool
        result = make_final_allocation_decision(focus_text)
        
        if result is None:
            return None
            
        result_str = str(result).strip()
        
        # Attempt to parse out the integer answer
        if result_str in ('0', '1', '2'):
            return int(result_str)
            
        # Try to find a keyword-based answer (e.g. "Option: 1", "The answer is 2")
        keyword_match = re.search(r'(?:choice|option|index|answer is|correct is|output:|answer:)\s*[:\*]*\s*([0-2])\b', result_str, re.IGNORECASE)
        if keyword_match:
            return int(keyword_match.group(1))
            
        # Fallback: Extract all occurrences of 0, 1, or 2 and apply heuristics
        matches = re.findall(r'\b([0-2])\b', result_str)
        if matches:
            if len(set(matches)) == 1:
                return int(matches[0])  # Only one distinct choice mentioned
            else:
                return int(matches[-1])  # Usually, the concluding answer is at the end of the generation
                
    except Exception:
        pass
        
    return None
