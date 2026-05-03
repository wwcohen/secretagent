"""Auto-generated workflow-distilled implementation for answer_question_workflow.

Calls existing tools from ptools_object.
"""

from ptools_object import *

def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    """Solve the object tracking and false belief task by orchestrating existing tools."""
    
    # Initialize module-level state if required by induced tools
    try:
        from ptools_common import _REACT_STATE
        _REACT_STATE['narrative'] = narrative
        _REACT_STATE['question'] = question
        _REACT_STATE['choices'] = choices
    except Exception:
        pass

    # Strategy 1: Full decomposed pipeline using positional arguments
    # (Matches the typical order of contextual chaining in ptools)
    try:
        movements = extract_movements(narrative)
        discoveries = extract_discoveries(narrative, movements)
        belief_text = infer_belief(narrative, movements, discoveries, question, choices)
        ans = extract_index(belief_text, choices)
        if isinstance(ans, int) and 0 <= ans < len(choices):
            return ans
    except Exception:
        pass

    # Strategy 2: Full decomposed pipeline using keyword arguments
    # (Extremely robust fallback if the induced tools use different parameter orders)
    try:
        movements = extract_movements(narrative=narrative)
        discoveries = extract_discoveries(narrative=narrative, movements=movements)
        belief_text = infer_belief(
            narrative=narrative, 
            movements=movements, 
            discoveries=discoveries, 
            question=question, 
            choices=choices
        )
        ans = extract_index(belief_text, choices)
        if isinstance(ans, int) and 0 <= ans < len(choices):
            return ans
    except Exception:
        pass

    # Strategy 3: Fallback to a single-tool ReAct solver
    try:
        solved_text = react_solve(narrative, question, choices)
        ans = extract_index(solved_text, choices)
        if isinstance(ans, int) and 0 <= ans < len(choices):
            return ans
    except Exception:
        pass

    # Strategy 4: Final fallback to raw basic answer
    try:
        raw_text = raw_answer(narrative, question, choices)
        ans = extract_index(raw_text, choices)
        if isinstance(ans, int) and 0 <= ans < len(choices):
            return ans
    except Exception:
        pass

    return None
