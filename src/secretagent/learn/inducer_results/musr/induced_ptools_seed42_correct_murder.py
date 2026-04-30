"""Induced ptools for MUSR murder (seed=42).

Auto-generated from results/20260411.021313.murder_react_train_seed42/results.jsonl.
Model: together_ai/deepseek-ai/DeepSeek-V3.
Do not edit — regenerate via generate_induced_configs.py.
"""

from secretagent.core import implement_via
from ptools.ptools_common import _REACT_STATE


@implement_via('simulate')
def _investigate_evidence_impl(narrative: str, focus: str) -> str:
    """
    Analyzes a murder mystery narrative for specific evidence types related to a focus (suspect, weapon, location, etc.).
    Extracts and evaluates evidence categories: means (weapon/ability), motive (reason to kill), opportunity (presence at scene),
    alibi consistency (verification of whereabouts), and physical evidence (direct forensic proof).

    Focuses on the specified target (person, role, evidence type) and returns structured analysis.
    Pay attention to: hard disqualifiers (ironclad alibis), conflicting evidence, reliability of witnesses,
    and evidence that might be misleading or require additional context.

    Returns:
    A structured string analysis organized by evidence category with bullet points.
    Example output format:
    "Analysis for [focus]:

    - Means: [evidence related to means]
    - Motive: [evidence related to motive]
    - Opportunity: [evidence related to presence/timing]
    - Alibi Consistency: [evidence supporting/contradicting alibi]
    - Physical Evidence: [forensic/direct evidence]

    Summary: [brief conclusion]"
    """


def investigate_evidence(focus: str) -> str:
    """Analyzes specific types of evidence in a murder mystery narrative to assess suspect culpability.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _investigate_evidence_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _initialize_suspect_analysis_impl(narrative: str, focus: str) -> str:
    """
    This function initiates the suspect analysis process for a murder mystery. It identifies the victim and all potential suspects mentioned in the narrative, then extracts initial clues and evidence related to each suspect. The function focuses on gathering foundational information about means, motive, opportunity, and any immediate physical evidence or alibis mentioned at the start of the case.

    The agent should pay attention to:
    - Correctly identifying all named suspects and the victim.
    - Noting any immediate disqualifiers (e.g., an explicit alibi mentioned early on).
    - Capturing initial clues without jumping to conclusions; this is just the starting point.
    - Being cautious of narrative red herrings or misleading initial information.

    The response is a structured JSON-shaped string containing the victim's name, a list of suspects, and a summary of initial evidence for each.

    Returns:
    A string formatted like:
    ```
    {
      "victim": "Name",
      "suspects": ["Suspect1", "Suspect2", ...],
      "initial_evidence": {
        "Suspect1": ["Brief clue 1", "Brief clue 2", ...],
        "Suspect2": ["Brief clue 1", ...],
        ...
      }
    }
    ```
    Example output:
    ```
    {
      "victim": "John Doe",
      "suspects": ["Alice", "Bob", "Charlie"],
      "initial_evidence": {
        "Alice": ["Was seen arguing with victim", "Has access to poison"],
        "Bob": ["Has no alibi for the time of murder"],
        "Charlie": ["Found with victim's watch"]
      }
    }
    ```
    """


def initialize_suspect_analysis(focus: str) -> str:
    """Initializes the analysis of suspects by identifying key individuals and extracting initial evidence from the narrative.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _initialize_suspect_analysis_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _determine_if_killer_impl(narrative: str, focus: str) -> str:
    """
    Evaluates whether the focused suspect is the murderer by analyzing the narrative.

    Key aspects to consider:
    - Means: Did the suspect have the capability/knowledge to commit the murder?
    - Motive: Did the suspect have a reason to want the victim dead?
    - Opportunity: Was the suspect present at the crime scene/able to commit the murder?
    - Alibi consistency: Does the suspect's alibi hold up under scrutiny?
    - Physical evidence: Is there concrete evidence linking the suspect to the crime?

    Hard disqualifiers:
    - Rock-solid alibi that places suspect elsewhere
    - Physical impossibility (wrong height/strength/access)
    - Contradictory evidence that completely exonerates

    Tricky aspects:
    - False alibis that appear convincing
    - Misdirection evidence
    - Multiple suspects with similar means/motive
    - Unreliable witness statements

    Returns:
    - '1' if the suspect is determined to be the killer
    - '0' if the suspect is determined not to be the killer

    Example return: '1'
    """


def determine_if_killer(focus: str) -> str:
    """Determine if the focused suspect is the killer based on means, motive, opportunity, alibi, and evidence.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _determine_if_killer_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _summarize_investigation_progress_impl(narrative: str, focus: str) -> str:
    """
    Summarizes the current investigation progress by analyzing key aspects of the case.

    Extracts and evaluates information about:
    - Means: Who had the capability/weapon to commit the murder
    - Motive: Who had reasons to want the victim dead
    - Opportunity: Who was present at the crime scene/time
    - Alibi consistency: Reliability of suspect alibis and timelines
    - Physical evidence: Forensic clues linking suspects to the crime

    Returns a structured JSON-shaped summary organized by suspect and category,
    including confidence levels and notable contradictions. The summary should
    highlight inconsistencies, strong/weak evidence, and potential disqualifiers.

    Pay special attention to:
    - Alibi verification and timeline conflicts
    - Contradictory witness statements
    - Physical evidence that confirms or refutes claims
    - Motive strength and plausibility
    - Opportunity windows and access requirements

    Returns:
    A JSON-shaped string with structure:
    {
      "case_overview": "brief summary of current status",
      "suspects": {
        "suspect_name": {
          "means": {"status": "confirmed/possible/unlikely", "details": "..."},
          "motive": {"status": "strong/weak/none", "details": "..."},
          "opportunity": {"status": "confirmed/possible/unlikely", "details": "..."},
          "alibi": {"consistency": "verified/contradicted/unverified", "details": "..."},
          "evidence": ["evidence_item_1", "evidence_item_2", ...]
        }
      },
      "key_contradictions": ["contradiction_1", "contradiction_2", ...],
      "next_steps": ["recommended_investigation_action_1", ...]
    }

    Example output:
    '{"case_overview": "Investigation ongoing with multiple viable suspects", "suspects": {"John": {"means": {"status": "confirmed", "details": "Had access to murder weapon"}, "motive": {"status": "strong", "details": "Financial dispute with victim"}, "opportunity": {"status": "possible", "details": "No solid alibi for crime window"}, "alibi": {"consistency": "contradicted", "details": "Witnesses contradict alibi claim"}, "evidence": ["Fingerprints on weapon"]}}, "key_contradictions": ["John's alibi contradicted by security footage"], "next_steps": ["Verify John's financial records"]}'
    """


def summarize_investigation_progress(focus: str) -> str:
    """Provides a structured summary of the current investigation status focusing on means, motive, opportunity, alibis, and evidence.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _summarize_investigation_progress_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _evaluate_suspect_evidence_impl(narrative: str, focus: str) -> str:
    """
    Evaluates evidence against a specific suspect in a murder mystery narrative by examining means, motive, opportunity, alibi consistency, and physical evidence.

    This function parses the provided narrative to extract and structure all relevant information
    that points to the guilt of the specified suspect. It focuses on identifying key pieces of
    evidence while noting potential weaknesses or alternative explanations.

    Args:
        narrative (str): The full text of the murder mystery narrative.
        focus (str): The name of the suspect to evaluate evidence against.

    Returns:
        str: A structured summary of evidence against the suspect, formatted as plain text with
             clear sections. The output includes:
             - A header specifying the suspect being evaluated
             - A bulleted list of evidence points, categorized by type (motive, means, opportunity, alibi, physical evidence)
             - Notes on any inconsistencies or counterarguments mentioned in the narrative
             - A brief overall assessment of the strength of the evidence

    Key considerations:
    - Pay close attention to direct physical evidence linking the suspect to the crime
    - Evaluate the strength and credibility of motives
    - Assess opportunity timelines and alibi consistency
    - Note any evidence that might exonerate the suspect or point to another party
    - Be aware of potential red herrings or misleading information in the narrative
    - Consider the reliability of witness statements and physical evidence descriptions

    Example output structure:
    \"\"\"
    Evidence against [suspect name]:

    Motive:
    - [Evidence point 1]
    - [Evidence point 2]

    Means:
    - [Evidence point 1]
    - [Evidence point 2]

    Opportunity:
    - [Evidence point 1]
    - [Evidence point 2]

    Physical Evidence:
    - [Evidence point 1]
    - [Evidence point 2]

    Alibi Assessment:
    - [Alibi consistency analysis]

    Overall Assessment:
    [Brief summary of evidence strength and key points]
    \"\"\"
    """


def evaluate_suspect_evidence(focus: str) -> str:
    """Analyzes the narrative to compile and weigh evidence against a specific suspect in a murder mystery.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _evaluate_suspect_evidence_impl(_REACT_STATE["narrative"], focus)
