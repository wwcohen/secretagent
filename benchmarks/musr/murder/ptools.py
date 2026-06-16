"""Interfaces for MUSR murder mystery reasoning.
"""

import sys
from pathlib import Path

from secretagent.core import interface
from secretagent.implement.pydantic import ToolFactory

#
# A plausible set of tools for the task.  Note most of these use the
# 'narrative' as an input, which can be large.
# 

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
def extract_index(answer_text: str, choices: list) -> int:
    """Given an answer and choices, return the 0-based index of the matching choice."""


@interface
def answer_question(narrative: str, question: str, choices: list) -> int:
    """Read the murder mystery narrative and answer the question.
    Return the 0-based index of the correct choice.
    """
    ...

#
# a function that can be used as direct implemenation of answer_question
#

def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    """Solve by extracting evidence, verifying alibis, deducing, then matching."""
    evidence = extract_suspects_and_evidence(narrative)
    verified = verify_alibis(narrative, evidence)
    text = deduce_murderer(narrative, verified, question, choices)
    return extract_index(text, choices)


#
# A ToolFactory variant for ReAct. To use this bind
#
#   ptools.answer_question.method=simulate_pydantic \
#   ptools.answer_question.tool_factory=ptools.MurderToolFactory
#
# When a new set of args is passed to the top_level_interface (ie
# answer_question) a new MurderToolFactory object is created and
# initialized (with the same args as answer_question).  The methods of
# MurderToolFactory share the state created at initialization - in
# this case class methods have access to 'narrative', which was stored
# at initialization.  When ReAct calls these methods it doesn't have
# insert the narrative into the call.

class MurderToolFactory(ToolFactory):
    """Per-call tool bundle for ReAct on a MUSR murder narrative.

    Stores the narrative on init() and exposes the three engineered
    sub-ptools as bound methods that auto-pass it. The agent threads
    structured evidence between steps; the long narrative string lives
    on ``self`` instead of being repeated on every tool call.
    """

    def __init__(self):
        self.narrative: str = ''

    def init(self, narrative, question, choices):
        # store the narrative
        self.narrative = narrative

    def solve_extract_suspects(self) -> str:
        """Extract the victim, crime details, and ALL suspects with their
        evidence from the current narrative.

        Call this FIRST. Returns structured suspect evidence — pass it to
        ``solve_verify_alibis``.
        """
        return extract_suspects_and_evidence(self.narrative)

    def solve_verify_alibis(self, suspect_evidence: str) -> str:
        """Re-read the narrative to verify or challenge each suspect's alibi.

        Call this SECOND, with the output of ``solve_extract_suspects``.
        Returns verified alibi analysis — pass it to ``solve_deduce_murderer``.
        """
        return verify_alibis(self.narrative, suspect_evidence)

    def solve_deduce_murderer(self, verified_analysis: str, question: str, choices: list) -> str:
        """Given verified alibi analysis and the answer choices, deduce who
        committed the murder.

        Call this LAST, with the output of ``solve_verify_alibis``. Returns
        a short string identifying the murderer (matching one of the
        choices). After this, decide the 0-based answer index and stop
        calling tools.
        """
        return deduce_murderer(self.narrative, verified_analysis, question, choices)

    def tools(self):
        return [self.solve_extract_suspects,
                self.solve_verify_alibis,
                self.solve_deduce_murderer]
