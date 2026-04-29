"""Auto-generated workflow-distilled implementation for are_sports_in_sentence_consistent.

Calls existing tools from ptools.
"""

from ptools import *

def are_sports_in_sentence_consistent(sentence: str) -> bool:
    """Check if the sports references in a sentence are consistent.
    
    Determines if the athlete mentioned plays the same sport as the 
    action/terminology/event described in the sentence.
    """
    # Use analyze_sentence to extract the athlete and action/sport elements
    try:
        analysis = analyze_sentence(sentence)
    except Exception:
        analysis = None
    
    if analysis is not None:
        # Try to use the structured approach
        try:
            # Get the sport for the player and the sport for the action
            # analysis might give us components we can check
            result = consistent_sports(analysis)
            if result is not None:
                return convert_llm_output_to_true_or_false(result)
        except Exception:
            pass
    
    # Fallback: use the sports_understanding_workflow which is described as
    # "Handcoded workflow for are_sports_in_sentence_consistent"
    try:
        result = sports_understanding_workflow(sentence)
        if result is not None:
            return result
    except Exception:
        pass
    
    # Another fallback: use zeroshot approach
    try:
        result = zeroshot_unstructured_workflow(sentence)
        if result is not None:
            return result
    except Exception:
        pass
    
    # Final fallback: use the zeroshot direct tool
    try:
        result = zeroshot_are_sports_in_sentence_consistent(sentence)
        if result is not None:
            return convert_llm_output_to_true_or_false(result)
    except Exception:
        pass
    
    return None
