"""Auto-generated workflow-distilled implementation for are_sports_in_sentence_consistent.

Calls existing tools from ptools.
"""

from ptools import *

def are_sports_in_sentence_consistent(sentence: str) -> bool:
    """Check if all sports references in a sentence are consistent.
    
    Extracts the athlete, action/terminology, and event from the sentence,
    determines which sport each belongs to, and checks if they all match.
    """
    # Use the analyze_sentence tool to extract sports-related components
    components = analyze_sentence(sentence)
    
    # Determine the sport for each component
    sports = []
    if isinstance(components, (list, tuple)):
        for component in components:
            if component:  # skip empty/None components
                sport = sport_for(component)
                if sport:
                    sports.append(sport)
    elif isinstance(components, dict):
        for key, value in components.items():
            if value:
                sport = sport_for(value)
                if sport:
                    sports.append(sport)
    elif isinstance(components, str):
        # If analyze_sentence returned a string, try using sport_for on individual parts
        # or fall back to consistent_sports directly
        result = consistent_sports(components)
        return convert_llm_output_to_true_or_false(result)
    
    if not sports:
        # Fallback: use consistent_sports on the whole sentence
        result = consistent_sports(sentence)
        return convert_llm_output_to_true_or_false(result)
    
    # Check if all identified sports are consistent
    if len(sports) <= 1:
        return True
    
    # Try using consistent_sports tool with the list of sports
    try:
        result = consistent_sports(sports)
        return convert_llm_output_to_true_or_false(result)
    except Exception:
        pass
    
    # Manual check: see if all sports are the same
    try:
        normalized = [str(s).strip().lower() for s in sports]
        return len(set(normalized)) == 1
    except Exception:
        return None
