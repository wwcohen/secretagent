"""Auto-generated workflow-distilled implementation for are_sports_in_sentence_consistent.

Calls existing tools from ptools.
"""

from ptools import *

def are_sports_in_sentence_consistent(sentence: str) -> bool:
    """Check if the sports references in a sentence are consistent.
    
    For example, if a hockey player is described as doing hockey things, 
    that's consistent (True). If a basketball player is described as 
    doing baseball things, that's inconsistent (False).
    """
    # Use analyze_sentence to extract the athlete and action/context from the sentence
    analysis = analyze_sentence(sentence)
    
    # The analysis likely contains the person and the action/event details
    # Use sport_for to determine the sport associated with each element
    # Then check consistency
    
    # Try to get sports for the different elements identified
    if isinstance(analysis, dict):
        # If analysis returns a dict with person and action info
        person = analysis.get('person', analysis.get('athlete', analysis.get('player', '')))
        action = analysis.get('action', analysis.get('activity', analysis.get('context', '')))
        
        person_sport = sport_for(person)
        action_sport = sport_for(action)
        
        return consistent_sports(person_sport, action_sport)
    elif isinstance(analysis, (list, tuple)):
        # If analysis returns a tuple/list of components
        # Likely (person, action) or (person, action, event) or similar
        sports = []
        for component in analysis:
            if component:
                sport = sport_for(component)
                if sport:
                    sports.append(sport)
        
        if len(sports) < 2:
            return True
        
        return consistent_sports(*sports)
    else:
        # analysis might be a string; try the direct approach
        # Fall back to using sport_for on the full sentence components
        # or use the zero-shot approach
        result = zeroshot_are_sports_in_sentence_consistent(sentence)
        return convert_llm_output_to_true_or_false(result)
