"""Interfaces for MUSR team allocation.

NOTE: A previous experiment with the single-ptool approach (answer_question
bound to simulate with thinking) outperformed early decomposed workflows
(84% vs 40-67%) — the LLM reasoned better about trade-offs holistically
than through lossy intermediate extraction.

The decomposed workflow below (extract_team_requirements +
score_team_assignments) is included as a hand-designed BASELINE for the
paper, not because it's expected to be the best — its purpose is to
isolate "human-designed library structure" from "induced library
structure" in a fair comparison.
"""

from secretagent.core import interface
from ptools_common import (  # noqa: F401  (re-export so the loaded ptools module exposes them)
    raw_answer,
    extract_index,
    react_solve,
)


@interface
def extract_team_requirements(narrative: str) -> str:
    """Extract the constraints and requirements that define a valid team.

    Read the narrative carefully and extract:

    Top level:
    - roles: list of roles the team needs to fill (e.g. "lead", "analyst",
      "support") with the headcount each role requires
    - hard_constraints: requirements that MUST hold for an assignment to
      be considered (e.g. "must have safety certification", "cannot pair
      X with Y", "needs at least one senior member")
    - soft_constraints: preferences that improve a team's score but are
      not strictly required (e.g. "prefer same-shift workers", "synergies
      between people with shared experience")
    - scoring_rules: any explicit numeric or qualitative scoring rule the
      narrative provides (e.g. "+2 if all members are bilingual",
      "score = sum of individual ratings")
    - synergies: pairs of people who work especially well together (only
      include pairs the narrative explicitly mentions)
    - conflicts: pairs of people who do NOT work well together (only
      include pairs the narrative explicitly mentions)

    Be exhaustive — don't omit constraints just because they sound minor.
    Use the exact names that appear in the story so they can be matched
    against the answer choices later. Do not invent constraints that the
    narrative does not state.
    """


@interface
def score_team_assignments(
    narrative: str,
    requirements: str,
    question: str,
    choices: list,
) -> str:
    """Score each candidate team assignment in the question's choices.

    You receive:
    1. The FULL original narrative (re-read it for details extraction may have missed)
    2. Extracted team requirements (roles, hard/soft constraints, scoring rules,
       synergies, conflicts)
    3. The question (which usually asks "what is the best assignment of people
       to roles?" or similar)
    4. The answer choices — each choice is a candidate assignment

    Your task — score each candidate assignment and identify the best one:

    For each candidate in choices:
      Step 1: List the (person, role) pairs the candidate proposes.
      Step 2: Check every hard_constraint. If ANY hard constraint is
              violated, mark the candidate INVALID and move on.
      Step 3: For valid candidates, count satisfied soft constraints
              and synergies; subtract for conflicts.
      Step 4: Apply any explicit scoring_rules from the narrative.
      Step 5: Produce a score (or qualitative ranking) for the candidate.

    After scoring all candidates:
      - Pick the candidate with the highest score (or the only valid one).
      - Briefly justify the choice by referencing the constraints that
        decided it.
      - End your response with the chosen assignment EXACTLY as it appears
        in the choices list, so the downstream extractor can match it.

    IMPORTANT: The narrative is the source of truth — if requirements
    extraction missed something, fall back to re-reading the narrative
    rather than inventing.
    """


@interface
def answer_question(narrative: str, question: str, choices: list) -> int:
    """Read the narrative and determine the best team allocation.
    Return the 0-based index of the correct choice.
    """
    text = raw_answer(narrative, question, choices)
    return extract_index(text, choices)


@interface
def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    """Solve by extracting team requirements, scoring assignments, then matching.

    3-step hand-designed workflow:
      1. extract_team_requirements — roles, constraints, scoring rules
      2. score_team_assignments — score each candidate against the requirements
      3. extract_index — match the chosen assignment to one of the choices
    """
    requirements = extract_team_requirements(narrative)
    text = score_team_assignments(narrative, requirements, question, choices)
    return extract_index(text, choices)


@interface
def holistic_think_and_solve(narrative: str, question: str, choices: list) -> str:
    """Holistically analyze the narrative to determine the best team allocation.

    You must think step-by-step:
    1. Identify the tasks and how many people each requires.
    2. Analyze the candidates' skills and weaknesses.
    3. Critically analyze interpersonal dynamics:
       - Identify any explicit conflicts (people who argue, dislike, blame, or have tension). NEVER pair them in the same multi-person task. This is a HARD RULE.
       - Identify explicit synergies (people who work well together). Pair them if possible.
       - If a candidate conflicts with both other people, isolate them in the 1-person task.

    Format your response EXACTLY as follows:
    THINKING:
    (your step-by-step reasoning here)

    CHOICE:
    (the EXACT text of the correct assignment from the choices list)
    """


# --- Auto-generated by orchestration_learner --seed-orchestrate ---
def answer_question_orchestrated_seed(narrative: str, question: str, choices: list) -> int:
    try:
        # Step 1: Perform holistic CoT reasoning
        response = holistic_think_and_solve(narrative, question, choices)
        
        # Step 2: Safely extract just the final choice text to avoid confusing extract_index
        final_text = response
        if response and "CHOICE:" in response:
            final_text = response.split("CHOICE:")[-1].strip()
            
        if not final_text:
            raise ValueError("Empty final text")
            
        # Step 3: Match against the choices list
        return extract_index(final_text, choices)
        
    except Exception:
        # Bulletproof fallback to the original zero-shot pipeline if anything goes wrong,
        # augmented with a critical hint to improve robustness.
        hint = "\n\nCRITICAL: Never pair conflicting people in the same multi-person task. Isolate them."
        answer_text = raw_answer(narrative + hint, question, choices)
        return extract_index(answer_text, choices)