"""Auto-generated workflow-distilled implementation for answer_question_workflow.

Calls existing tools from ptools_team.
"""

from ptools_team import *

def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    """Solve team assignment problems by extracting requirements, scoring assignments, and picking the best."""
    try:
        # Step 1: Extract team requirements (skills, strengths, weaknesses of each person)
        requirements = extract_team_requirements(narrative)
        
        # Step 2: Score each possible team assignment against the requirements
        scores = score_team_assignments(narrative, requirements, question, choices)
        
        # Step 3: Extract the index from the scoring result
        result = extract_index(scores, choices)
        
        # Validate result
        if result is not None and isinstance(result, int) and 0 <= result < len(choices):
            return result
    except Exception:
        pass
    
    # Fallback approach: use direct answer_question
    try:
        result = answer_question(narrative, question, choices)
        if result is not None and isinstance(result, int) and 0 <= result < len(choices):
            return result
    except Exception:
        pass
    
    # Second fallback: use raw_answer + extract_index
    try:
        text = raw_answer(narrative, question, choices)
        result = extract_index(text, choices)
        if result is not None and isinstance(result, int) and 0 <= result < len(choices):
            return result
    except Exception:
        pass
    
    return None
