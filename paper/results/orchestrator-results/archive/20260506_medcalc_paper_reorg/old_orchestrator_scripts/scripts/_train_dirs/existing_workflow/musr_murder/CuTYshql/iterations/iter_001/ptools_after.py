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
    find logical weaknesses.

    For each suspect, determine:
    - alibi_claim: What exactly do they say they were doing?
    - relevant_facts: What subtle facts in the narrative relate to their claim? (e.g., weather conditions, operating hours, personal habits, broken items, physical constraints)
    - contradictions: Is their claim logically impossible or directly contradicted by the established facts?
    - alibi_status: Can the alibi be verified, or is it a lie?

    Pay special attention to:
    - Claims of doing an activity that was impossible at the time (e.g., gardening in the pitch dark, using a broken item).
    - Claims of being at a location that was closed, locked, or inaccessible.
    - Suspects acting completely contrary to their strongly established defining traits without a valid explanation.
    """


@interface
def deduce_murderer(narrative: str, verified_analysis: str, question: str, choices: list) -> str:
    """Given the original narrative, verified alibi analysis, and answer choices,
    deduce who committed the murder.

    You have access to:
    1. The FULL original narrative
    2. Verified analysis for each suspect (alibi status, gaps, contradictions)
    3. The multiple-choice options

    CRITICAL RULES FOR DEDUCTION:
    1. Both suspects usually have a plausible motive and access to the means.
    2. DO NOT simply pick the suspect who owns the murder weapon. Obvious physical evidence (like owning the weapon type) is very often a RED HERRING meant to frame the innocent suspect.
    3. The true murderer is the suspect caught in a LOGICAL LIE. You must find the subtle factual contradiction in a suspect's alibi or statements.
    4. Compare what each suspect claims to be doing with the background facts established in the narrative.
    5. The suspect whose story is factually impossible or contains a direct contradiction is the murderer.

    Your task:
    - Synthesize all evidence.
    - Identify which suspect's alibi contains a logical flaw or contradiction.
    - Deduce the murderer based primarily on this inconsistency, ignoring red herrings.
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