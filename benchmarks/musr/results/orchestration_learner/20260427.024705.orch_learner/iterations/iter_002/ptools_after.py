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

import re
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
      not strictly required
    - scoring_rules: any explicit numeric or qualitative scoring rule the
      narrative provides
    - synergies: pairs of people who work especially well together
    - conflicts: pairs of people who do NOT work well together (e.g. argue, 
      dislike, blame). This is a FATAL constraint.

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
      Step 3: Check INTERPERSONAL CONSTRAINTS:
              - NEVER assign two people who conflict (argue, dislike, blame) to the same 2-person task. Mark INVALID.
              - If a person conflicts with BOTH other people, they MUST be assigned to the 1-person task.
      Step 4: For valid candidates, count satisfied soft constraints
              and synergies; subtract for conflicts.
      Step 5: Apply any explicit scoring_rules from the narrative.
      Step 6: Produce a score (or qualitative ranking) for the candidate.

    After scoring all candidates:
      - Pick the candidate with the highest score (or the only valid one).
      - Briefly justify the choice by referencing the constraints that decided it.
      - End your response with the chosen assignment EXACTLY as it appears
        in the choices list, so the downstream extractor can match it.
    """


@interface
def analyze_team_allocation(narrative: str, question: str, choices: list) -> str:
    """Analyze the narrative and evaluate the team allocation choices.

    Think step-by-step:
    1. Identify the 3 team members and the 2 tasks from the choices. Determine which task requires 1 person and which requires 2.
    2. Interpersonal Dynamics:
       - Conflicts: Who explicitly argues, dislikes, blames, or has tension with whom?
       - Synergies: Who has a successful history or bond with whom?
    3. Skills & Weaknesses: Note who is uniquely qualified or explicitly unqualified (e.g. fear, incompetence) for a specific task.
    4. Evaluate Choices:
       - HARD RULE: NEVER group two people who have a conflict into the same 2-person task.
       - HARD RULE: If a person conflicts with BOTH of the other two, they MUST be isolated in the 1-person task.
       - HARD RULE: Group people with strong synergies into the 2-person task if possible.
       - SOFT RULE: Match people to tasks based on their skills and avoid their weaknesses.
    5. Conclusion: Select the best choice based on the rules.
    
    You MUST conclude your response by printing the exact text of the chosen assignment enclosed in <FINAL_CHOICE> tags.
    Example: <FINAL_CHOICE>Task A: Person X, Task B: Person Y and Person Z</FINAL_CHOICE>
    """


@interface
def answer_question(narrative: str, question: str, choices: list) -> int:
    """Read the narrative and determine the best team allocation.
    
    Think step-by-step:
    1. Interpersonal Dynamics: Note conflicts (arguments, tension) and synergies (bonds).
    2. HARD RULES: 
       - NEVER pair conflicting people in the same task.
       - If someone conflicts with BOTH others, isolate them in the 1-person task.
       - ALWAYS pair people with strong synergy.
    3. Evaluate choices and select the best one.
    
    Return ONLY the 0-based index of the correct choice.
    """
    analysis = analyze_team_allocation(narrative, question, choices)
    
    match = re.search(r'<FINAL_CHOICE>(.*?)</FINAL_CHOICE>', analysis, re.IGNORECASE | re.DOTALL)
    if match:
        final_str = match.group(1).strip().lower()
        for i, c in enumerate(choices):
            if final_str == c.lower():
                return i
        for i, c in enumerate(choices):
            if c.lower() in final_str or final_str in c.lower():
                return i
                
    # Fallback to extraction LLM if tags fail
    augmented_question = f"{question}\n\n=== EXPERT ANALYSIS ===\n{analysis}\n\nBased on the analysis, output ONLY the exact string of the best choice."
    text = raw_answer(narrative, augmented_question, choices)
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


# --- Auto-generated by orchestration_learner --seed-orchestrate ---
def answer_question_orchestrated_seed(narrative: str, question: str, choices: list) -> int:
    analysis = analyze_team_allocation(narrative, question, choices)
    
    # Try exact or substring regex match for highest reliability
    match = re.search(r'<FINAL_CHOICE>(.*?)</FINAL_CHOICE>', analysis, re.IGNORECASE | re.DOTALL)
    if match:
        final_str = match.group(1).strip().lower()
        for i, c in enumerate(choices):
            if final_str == c.lower():
                return i
        for i, c in enumerate(choices):
            if c.lower() in final_str or final_str in c.lower():
                return i
                
    # Fallback if no tags are provided by the LLM
    augmented_question = f"{question}\n\n=== EXPERT ANALYSIS ===\n{analysis}\n\nBased on the analysis, output ONLY the exact string of the best choice."
    text = raw_answer(narrative, augmented_question, choices)
    return extract_index(text, choices)