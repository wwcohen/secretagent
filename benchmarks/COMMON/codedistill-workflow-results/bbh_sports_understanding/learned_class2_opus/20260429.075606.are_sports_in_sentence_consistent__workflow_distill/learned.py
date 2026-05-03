"""Auto-generated workflow-distilled implementation for are_sports_in_sentence_consistent.

Calls existing tools from ptools.
"""

from ptools import *

def are_sports_in_sentence_consistent(sentence: str) -> bool:
    """Determine if the sports referenced in a sentence are all consistent.
    
    Extracts the player, action, and optional event from the sentence,
    determines the sport for each, and checks consistency.
    """
    try:
        # Step 1: Analyze the sentence to extract player, action, and event
        result = analyze_sentence(sentence)
        
        # Defensive: make sure we got a tuple of 3
        if not isinstance(result, (tuple, list)) or len(result) != 3:
            return None
        
        player, action, event = result
        
        # Step 2: Determine the sport for the player and action
        player_sport = sport_for(player)
        action_sport = sport_for(action)
        
        if player_sport is None or action_sport is None:
            return None
        
        # Step 3: Check consistency between player sport and action sport
        result = consistent_sports(player_sport, action_sport)
        
        if result is None:
            return None
        
        # Step 4: If there's an event, also check consistency with that
        if event and event.strip():
            event_sport = sport_for(event)
            if event_sport is None:
                return None
            event_consistent = consistent_sports(player_sport, event_sport)
            if event_consistent is None:
                return None
            result = result and event_consistent
        
        # Ensure we return a bool
        if isinstance(result, bool):
            return result
        
        # Try to coerce to bool defensively
        if result is None:
            return None
        
        return bool(result)
    
    except Exception:
        return None
