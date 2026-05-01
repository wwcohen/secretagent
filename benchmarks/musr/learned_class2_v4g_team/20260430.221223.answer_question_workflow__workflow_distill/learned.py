"""Auto-generated workflow-distilled implementation for answer_question_workflow.

Calls existing tools from ptools_team.
"""

from ptools_team import *

def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    try:
        # Step 1: Extract the team member requirements, strengths, weaknesses, and constraints
        reqs = extract_team_requirements(narrative)
        if not reqs:
            return None
            
        # Step 2: Score/evaluate the possible team assignments against the extracted requirements
        evaluation = score_team_assignments(narrative, reqs, question, choices)
        if not evaluation:
            return None
            
        # Step 3: Extract the 0-based index of the best assignment from the evaluation
        idx = extract_index(evaluation, choices)
        
        # Handle potential type inconsistencies and validate bounds
        if isinstance(idx, str):
            try:
                idx = int(idx.strip())
            except ValueError:
                return None
                
        if isinstance(idx, int) and 0 <= idx < len(choices):
            return idx
            
    except Exception:
        # Fallback to None (which triggers zero-shot fallback) if any tool raises an error
        pass
        
    return None
