"""Auto-generated workflow-distilled implementation for answer_question.

Tools from /Users/yanjiarui/Desktop/Will_research/secretagent/benchmarks/musr/learned_class3/20260428.104811.answer_question__ptool_inducer/learned_ptools.py are inlined below.
"""

"""Induced ptools for answer_question."""

from secretagent.core import implement_via
from ptools_common import _REACT_STATE


@implement_via('simulate')
def _gather_evidence_impl(context: str, focus: str) -> str:
    """
    This function analyzes a murder mystery narrative to find and return evidence specifically related to a given focus (e.g., a person, object, location, or motive).
    The function should search the context for any statements, clues, or facts that directly relate to the focus. The response should be structured as a list of concise evidence points, each clearly tied to the focus.
    Pay close attention to details in the narrative that may be directly or indirectly linked to the focus, including alibis, motives, opportunities, physical evidence, or witness statements.
    Returns: A structured string listing all relevant evidence found, or a statement that no evidence was found.

    Example:
    For context='The revolver was found near the victim. Randy had financial troubles.' and focus='revolver',
    Returns:
    "Relevant evidence found for 'revolver':
    - The revolver was found near the victim."
    """


def gather_evidence(focus: str) -> str:
    """Extracts and returns specific evidence from a narrative based on a given focus."""
    return _gather_evidence_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _search_suspect_attributes_impl(context: str, focus: str) -> str:
    """
    Extracts and analyzes information from the context regarding a specific suspect's attributes.
    Focuses on finding evidence related to motive (reasons to commit the crime), opportunity (being present at the crime scene/time), access (means to commit the crime), or suspicious behavior.
    The response should be structured as a concise summary of relevant evidence found, highlighting key details.
    Pay attention to: direct statements, implied clues, relationships, timings, locations, and objects mentioned.
    Returns: A string summarizing the evidence found, or 'No relevant evidence found.' if none.
    Example output: 'Evidence found: Suspect had a financial motive (inheritance). Was seen near the crime scene at the time. Had access to the murder weapon (knife).'
    """


def search_suspect_attributes(focus: str) -> str:
    """Search the narrative for evidence related to a suspect's motive, opportunity, access, or suspicious behavior."""
    return _search_suspect_attributes_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _analyze_and_synthesize_evidence_impl(context: str, focus: str) -> str:
    """
    Analyzes available evidence from a murder mystery narrative to determine which suspect is most likely guilty.

    Extracts and evaluates evidence related to:
    - Means: access to/use of murder weapon
    - Motive: reasons for committing the crime
    - Opportunity: presence at crime scene/timing
    - Direct vs circumstantial evidence
    - Suspect statements and behaviors

    Response should be structured as:
    1. List key evidence points for each suspect
    2. Compare evidence strength across suspects
    3. Identify which evidence is most compelling
    4. Conclude which suspect is most likely guilty

    Pay attention to:
    - Physical evidence vs circumstantial evidence
    - Direct witness statements vs assumptions
    - Conflicting alibis or statements
    - Timeline consistency
    - Weapon access and expertise

    Returns:
    A structured analysis ending with a conclusion about the most likely murderer.

    Example output:
    "Based on the evidence gathered:

    1. Suspect A had access to the murder weapon and was seen near the scene
    2. Suspect B had motive but no direct evidence linking them
    3. Suspect C had opportunity but no clear motive

    The physical evidence and witness statements point most strongly to Suspect A."
    """


def analyze_and_synthesize_evidence(focus: str) -> str:
    """Analyzes evidence against suspects and synthesizes the most compelling case for who committed the murder."""
    return _analyze_and_synthesize_evidence_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _form_conclusion_impl(context: str, focus: str) -> str:
    """
    Forms a conclusion about a specific suspect's guilt based on the provided narrative evidence.

    This function analyzes the provided context (narrative) to determine if the specified suspect
    committed the murder. It should focus on extracting and evaluating direct evidence, alibis,
    motives, and opportunities presented in the text that are specifically related to the focus suspect.

    The response should be a structured string containing a binary conclusion (1 for guilty, 0 for not guilty)
    followed by a concise, evidence-based justification. The justification should directly reference
    key facts from the narrative that support the conclusion.

    Pay close attention to:
    - Contradictions in alibis or statements
    - Physical evidence linking the suspect to the crime
    - Motive and opportunity
    - Testimony from other characters
    - Any direct admissions or actions described

    Returns:
        str: A string in the format "{conclusion}|{justification}"
        Example: "1|The suspect's fingerprints were found on the murder weapon and they were seen leaving the scene."
    """


def form_conclusion(focus: str) -> str:
    """Forms a conclusion about a specific suspect's guilt based on the provided narrative evidence."""
    return _form_conclusion_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _plan_investigation_approach_impl(context: str, focus: str) -> str:
    """
    Analyzes the murder mystery narrative and question to develop a structured investigation plan.

    This tool identifies the key suspects from the multiple-choice options, determines what evidence
    needs to be gathered about each suspect, and outlines a systematic approach for using available
    tools (search, lookup) to collect relevant information. The response should focus on creating
    a logical investigation strategy rather than drawing conclusions.

    Key considerations:
    - Extract suspect names from the multiple-choice options
    - Identify potential evidence types relevant to murder investigations (alibis, motives, opportunities, relationships)
    - Plan targeted searches for each suspect and related evidence
    - Consider timeline analysis, witness statements, and forensic evidence mentioned in the narrative
    - Structure the approach to systematically eliminate or implicate suspects

    Returns:
    A structured string containing:
    - Suspects identified from choices
    - Key investigation areas for each suspect
    - Recommended search terms and evidence types
    - Overall investigation strategy

    Example output:
    "Suspects: ['Isla', 'Randy']
    Investigation plan:
    - Search for Isla's alibi, motive, and timeline
    - Search for Randy's alibi, motive, and timeline  
    - Lookup crime scene evidence related to both suspects
    - Analyze witness statements mentioning either suspect
    - Compare opportunities and means for both suspects"
    """


def plan_investigation_approach(focus: str) -> str:
    """Plans an investigative strategy for solving a murder mystery by identifying key suspects and evidence search priorities."""
    return _plan_investigation_approach_impl(_REACT_STATE["narrative"], focus)




def answer_question(narrative, question, choices):
    import ast
    import re
    
    # Parse choices if it's a string
    if isinstance(choices, str):
        try:
            choices = ast.literal_eval(choices)
        except:
            return None
    
    # Initialize the state so tools can read the narrative
    try:
        from ptools_common import _REACT_STATE
        _REACT_STATE['narrative'] = narrative
        _REACT_STATE['question'] = question
        _REACT_STATE['choices'] = choices
    except ImportError:
        pass
    
    # Gather evidence for each suspect
    suspect_evidence = {}
    for suspect in choices:
        try:
            evidence = gather_evidence(f"Evidence about {suspect} including motive, opportunity, means, and suspicious behavior")
            suspect_evidence[suspect] = evidence
        except:
            suspect_evidence[suspect] = ""
    
    # Search suspect attributes
    suspect_attrs = {}
    for suspect in choices:
        try:
            attrs = search_suspect_attributes(f"{suspect} motive opportunity access suspicious behavior murder weapon")
            suspect_attrs[suspect] = attrs
        except:
            suspect_attrs[suspect] = ""
    
    # Analyze and synthesize evidence comparing suspects
    suspects_str = " versus ".join(choices)
    try:
        synthesis = analyze_and_synthesize_evidence(
            f"Compare {suspects_str} to determine who most likely committed the murder. {question} Choices: {choices}"
        )
    except:
        synthesis = ""
    
    # Form conclusions for each suspect
    conclusions = {}
    for suspect in choices:
        try:
            conclusion = form_conclusion(
                f"Is {suspect} the murderer? Evaluate all evidence for {suspect} including motive, opportunity, means, and behavior."
            )
            conclusions[suspect] = conclusion
        except:
            conclusions[suspect] = ""
    
    # Try to determine the answer from synthesis and conclusions
    # Look for explicit mentions of guilt in synthesis
    if synthesis:
        synthesis_lower = synthesis.lower()
        # Check which suspect is more strongly implicated
        scores = [0] * len(choices)
        for i, suspect in enumerate(choices):
            name_lower = suspect.lower()
            if f"{name_lower} is the most likely" in synthesis_lower or f"{name_lower} committed" in synthesis_lower:
                scores[i] += 3
            if f"{name_lower} is guilty" in synthesis_lower or f"{name_lower} is the killer" in synthesis_lower:
                scores[i] += 3
            if f"{name_lower} had access" in synthesis_lower or f"{name_lower} had motive" in synthesis_lower:
                scores[i] += 1
            if f"evidence points to {name_lower}" in synthesis_lower or f"pointing to {name_lower}" in synthesis_lower:
                scores[i] += 2
            # Check for conclusion format "index|..."
            if suspect in conclusions:
                c = conclusions[suspect]
                if c.startswith("1|") or c.startswith("1 |"):
                    scores[i] += 3
                elif c.startswith("0|") or c.startswith("0 |"):
                    pass  # no addition
        
        if max(scores) > 0 and scores.count(max(scores)) == 1:
            return scores.index(max(scores))
    
    # Fallback: use form_conclusion with a direct question
    try:
        direct = form_conclusion(
            f"Between {' and '.join(choices)}, who is the most likely murderer? Return the name."
        )
        if direct:
            for i, suspect in enumerate(choices):
                if suspect.lower() in direct.lower():
                    # Check it's not just mentioning both
                    other_mentions = sum(1 for j, s in enumerate(choices) if j != i and s.lower() in direct.lower())
                    if other_mentions == 0:
                        return i
    except:
        pass
    
    # If we can't confidently determine, return None to fall back to LLM
    return None
