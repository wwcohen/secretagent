"""Auto-generated workflow-distilled implementation for answer_question_workflow.

Calls existing tools from ptools_murder.
"""

from ptools_murder import *

def answer_question_workflow(narrative, question, choices):
    """Determine the most likely murderer from a mystery narrative."""
    
    # Try using deduce_murderer first
    try:
        murderer_name = deduce_murderer(narrative, question, choices)
        if murderer_name is not None:
            # Try to extract the index from the name
            murderer_str = str(murderer_name).strip()
            # Check if it's already an index
            try:
                idx = int(murderer_str)
                if 0 <= idx < len(choices):
                    return idx
            except (ValueError, TypeError):
                pass
            # Try matching against choices
            for i, choice in enumerate(choices):
                if choice.lower().strip() == murderer_str.lower().strip():
                    return i
            # Try partial matching
            for i, choice in enumerate(choices):
                if choice.lower() in murderer_str.lower() or murderer_str.lower() in choice.lower():
                    return i
    except Exception:
        pass
    
    # Try using answer_question as a backup
    try:
        result = answer_question(narrative, question, choices)
        if result is not None:
            # If it's already an int
            if isinstance(result, int) and 0 <= result < len(choices):
                return result
            result_str = str(result).strip()
            try:
                idx = int(result_str)
                if 0 <= idx < len(choices):
                    return idx
            except (ValueError, TypeError):
                pass
            for i, choice in enumerate(choices):
                if choice.lower().strip() == result_str.lower().strip():
                    return i
            for i, choice in enumerate(choices):
                if choice.lower() in result_str.lower() or result_str.lower() in choice.lower():
                    return i
    except Exception:
        pass
    
    # Try extract_suspects_and_evidence + raw_answer approach
    try:
        evidence = extract_suspects_and_evidence(narrative)
        if evidence is not None:
            raw = raw_answer(narrative, question, choices, str(evidence))
            if raw is not None:
                raw_str = str(raw).strip()
                try:
                    idx = int(raw_str)
                    if 0 <= idx < len(choices):
                        return idx
                except (ValueError, TypeError):
                    pass
                for i, choice in enumerate(choices):
                    if choice.lower().strip() == raw_str.lower().strip():
                        return i
                for i, choice in enumerate(choices):
                    if choice.lower() in raw_str.lower() or raw_str.lower() in choice.lower():
                        return i
    except Exception:
        pass
    
    # Try react_solve as final attempt
    try:
        result = react_solve(narrative, question, choices)
        if result is not None:
            if isinstance(result, int) and 0 <= result < len(choices):
                return result
            result_str = str(result).strip()
            try:
                idx = int(result_str)
                if 0 <= idx < len(choices):
                    return idx
            except (ValueError, TypeError):
                pass
            for i, choice in enumerate(choices):
                if choice.lower().strip() == result_str.lower().strip():
                    return i
            for i, choice in enumerate(choices):
                if choice.lower() in result_str.lower() or result_str.lower() in choice.lower():
                    return i
    except Exception:
        pass
    
    # Return None to fall back to pure-LLM zero-shot
    return None
