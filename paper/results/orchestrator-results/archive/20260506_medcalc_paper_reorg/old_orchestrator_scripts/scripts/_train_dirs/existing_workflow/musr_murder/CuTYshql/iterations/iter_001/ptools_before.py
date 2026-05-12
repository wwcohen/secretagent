"""Interfaces for MUSR murder mystery reasoning.

Migrated from AgentProject v2 ptools. Design principle: ptools ANNOTATE
and ENHANCE reasoning on the raw narrative, rather than abstracting it
away into lossy structured data.
"""

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
    - suspects: for each suspect, extract the following

    For each suspect, extract:
    - motive: why they might have killed the victim
    - means: access to weapon, relevant skills/knowledge
    - opportunity: were they near the crime scene, timeline gaps
    - alibi_claim: what they say they were doing
    - alibi_witnesses: people/evidence that could verify their alibi
    - suspicious_behavior: nervousness, contradictions, cleanup, lies
    - physical_evidence: weapon found at their place, forensics, DNA, fingerprints

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
    - Synthesize all evidence
    - Consider which suspect has the WEAKEST alibi combined with the STRONGEST evidence against them
    - Weight physical evidence heavily (fingerprints, DNA, weapon possession)
    - Weight alibi contradictions by third parties heavily
    - Consider motive as supporting but not sufficient alone
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
    return extract_index(text, choices)
