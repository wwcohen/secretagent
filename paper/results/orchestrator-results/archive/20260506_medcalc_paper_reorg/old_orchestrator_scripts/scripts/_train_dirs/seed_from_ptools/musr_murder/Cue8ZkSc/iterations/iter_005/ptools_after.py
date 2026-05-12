"""Interfaces for MUSR murder mystery reasoning.

Migrated from AgentProject v2 ptools. Design principle: ptools ANNOTATE
and ENHANCE reasoning on the raw narrative, rather than abstracting it
away into lossy structured data.
"""

import re
from secretagent.core import interface
from ptools_common import (  # noqa: F401  (re-export so the loaded ptools module exposes them)
    raw_answer,
    extract_index,
    react_solve,
)


@interface
def extract_suspects_and_evidence(narrative: str) -> str:
    """Extract the victim, crime details, and ALL suspects with their evidence.

    Read the narrative carefully and extract:

    Top level:
    - victim: name of the murdered person
    - crime_details: how/where they were killed, when body was found
    - murder_weapon: the EXACT description of the weapon used at the crime scene
    - suspects: for each suspect, extract the following

    For each suspect, extract:
    - motive: why they might have killed the victim
    - means: access to weapon, relevant skills/knowledge
    - opportunity: were they near the crime scene, timeline gaps
    - alibi_claim: what they say they were doing
    - alibi_witnesses: people/evidence that could verify their alibi
    - suspicious_behavior: nervousness, contradictions, cleanup, lies
    - physical_evidence: weapon found at their place, forensics, DNA, fingerprints. Note if their weapon is an EXACT match to the murder weapon, or just a similar type/replica.

    Be thorough — include EVERY suspect mentioned. Do NOT omit anyone.
    Include the victim's name so downstream analysis knows who was killed.
    """


@interface
def verify_alibis(narrative: str, suspect_evidence: str) -> str:
    """Re-read the narrative to verify or challenge each suspect's alibi.

    You receive the original narrative AND structured evidence extracted
    for each suspect. Cross-reference alibis against the narrative to
    find weaknesses.

    For each suspect, determine:
    - alibi_holds: can the alibi actually be confirmed?
    - alibi_gaps: any unexplained time periods
    - contradictions: inconsistencies in their story vs narrative facts
    - weapon_link: does their associated weapon EXACTLY match the crime scene weapon, or is it circumstantial/replica?
    - corroborating_evidence: evidence that supports or refutes involvement

    Pay special attention to:
    - Witnesses who contradict the suspect's claims
    - Time gaps between when alibis end and the crime window
    - Physical evidence that places them at the scene
    - Statements that are plausible but unverifiable
    """


@interface
def deduce_murderer(narrative: str, verified_analysis: str, question: str, choices: list) -> str:
    """Given the original narrative, verified alibi analysis, and answer choices,
    deduce who committed the murder.

    You have access to:
    1. The FULL original narrative — re-read it for details the analysis may have missed
    2. Verified analysis for each suspect (alibi status, gaps, contradictions, evidence)
    3. The multiple-choice options

    Your task:
    - Think step-by-step and write out your reasoning to synthesize all evidence.
    - IMPORTANT: Use bullet points (-) instead of numbered lists (1., 2.) to avoid confusing the extraction logic.
    - Compare the two suspects side-by-side, evaluating their means, motive, opportunity, and alibi.
    - Pay close attention to the EXACT weapon used. If the narrative specifies an "antique" weapon, a "replica", or a specific origin, match this precisely to the suspects.
    - Consider which suspect has the WEAKEST alibi combined with the STRONGEST evidence against them.
    - Weight physical evidence heavily (fingerprints, DNA, weapon possession), but carefully ensure it aligns with a realistic timeline and opportunity.
    - Weight alibi contradictions by third parties heavily. Unverified or directly contradicted alibis are strong indicators of guilt.
    - Consider motive as supporting but not sufficient alone.
    - Conclude your reasoning by explicitly stating your final choice from the options on a new line.
      Example: "Final Answer: John Doe"
    """


@interface
def answer_question(narrative: str, question: str, choices: list) -> int:
    """Read the murder mystery narrative and answer the question.
    Return the 0-based index of the correct choice.
    """
    text = raw_answer(narrative, question, choices)
    return extract_index(text, choices)


@interface
def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    """Solve by extracting evidence, verifying alibis, deducing, then matching."""
    evidence = extract_suspects_and_evidence(narrative)
    verified = verify_alibis(narrative, evidence)
    text = deduce_murderer(narrative, verified, question, choices)
    
    # Safely extract final answer to prevent extract_index from getting confused by numbered lists
    match = re.search(r'Final\s*Answer:\s*([^\n]+)', text, re.IGNORECASE)
    if match:
        ans = match.group(1).strip()
        for c in sorted(choices, key=len, reverse=True):
            if c.lower() in ans.lower():
                return choices.index(c)
                
    return extract_index(text, choices)


# --- Auto-generated by orchestration_learner --seed-orchestrate ---
def answer_question_workflow_orchestrated_seed(narrative: str, question: str, choices: list) -> int:
    suspects_and_evidence = extract_suspects_and_evidence(narrative)
    verified_alibis = verify_alibis(narrative, suspects_and_evidence)
    murderer_deduction = deduce_murderer(narrative, verified_alibis, question, choices)
    
    # Safely extract final answer to prevent extract_index from getting confused by numbered lists
    match = re.search(r'Final\s*Answer:\s*([^\n]+)', murderer_deduction, re.IGNORECASE)
    if match:
        ans = match.group(1).strip()
        for c in sorted(choices, key=len, reverse=True):
            if c.lower() in ans.lower():
                return choices.index(c)
                
    final_index = extract_index(murderer_deduction, choices)
    return final_index