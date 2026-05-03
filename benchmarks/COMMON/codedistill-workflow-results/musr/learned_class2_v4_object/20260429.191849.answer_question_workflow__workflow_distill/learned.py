"""Auto-generated workflow-distilled implementation for answer_question_workflow.

Calls existing tools from ptools_object.
"""

from ptools_object import *

def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    """Solve theory-of-mind object-tracking questions by extracting movements,
    discoveries, inferring beliefs, then matching to choices."""
    
    # Step 1: Extract all object movements from the narrative
    try:
        movements = extract_movements(narrative)
    except Exception:
        movements = ""
    
    # Step 2: Extract what each character discovers/learns about object locations
    try:
        discoveries = extract_discoveries(narrative)
    except Exception:
        discoveries = ""
    
    # Step 3: Combine movements and discoveries to infer the specific character's belief
    combined_info = ""
    if movements:
        combined_info += "Object movements:\n" + str(movements) + "\n\n"
    if discoveries:
        combined_info += "Character discoveries:\n" + str(discoveries) + "\n\n"
    
    try:
        belief = infer_belief(narrative, combined_info, question, choices)
    except Exception:
        belief = None
    
    # Step 4: Extract the index from the belief answer
    if belief:
        try:
            idx = extract_index(str(belief), choices)
            if idx is not None and isinstance(idx, int) and 0 <= idx < len(choices):
                return idx
        except Exception:
            pass
    
    # Fallback: try the direct raw_answer approach
    try:
        text = raw_answer(narrative, question, choices)
        if text:
            idx = extract_index(str(text), choices)
            if idx is not None and isinstance(idx, int) and 0 <= idx < len(choices):
                return idx
    except Exception:
        pass
    
    # Final fallback: try answer_question directly
    try:
        idx = answer_question(narrative, question, choices)
        if idx is not None and isinstance(idx, int) and 0 <= idx < len(choices):
            return idx
    except Exception:
        pass
    
    # Return None to trigger zero-shot fallback
    return None
