"""Auto-generated workflow-distilled implementation for are_sports_in_sentence_consistent.

Calls existing tools from ptools.
"""

from ptools import *

def are_sports_in_sentence_consistent(sentence: str) -> bool:
    try:
        analyzed = analyze_sentence(sentence)
        if not isinstance(analyzed, (tuple, list)) or len(analyzed) != 3:
            return None
            
        player, action, event = analyzed
        
        # Validate that player and action are valid non-empty strings
        if not isinstance(player, str) or not player.strip():
            return None
        if not isinstance(action, str) or not action.strip():
            return None
        if not isinstance(event, str):
            return None

        # Fetch the sport associated with the player and the action
        player_sport = sport_for(player)
        action_sport = sport_for(action)
        
        if not isinstance(player_sport, str) or not player_sport.strip():
            return None
        if not isinstance(action_sport, str) or not action_sport.strip():
            return None
            
        # Check if the player's sport and action's sport are consistent
        result = consistent_sports(player_sport, action_sport)
        
        # Helper to safely handle boolean coercion
        def _to_bool(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                s = val.strip().lower()
                if s == 'true': return True
                if s == 'false': return False
            return None
            
        result_bool = _to_bool(result)
        if result_bool is None:
            return None
            
        # If there's an event mentioned, it must also be consistent with the player's sport
        if event.strip():
            event_sport = sport_for(event)
            if not isinstance(event_sport, str) or not event_sport.strip():
                return None
                
            event_result = consistent_sports(player_sport, event_sport)
            event_result_bool = _to_bool(event_result)
            
            if event_result_bool is None:
                return None
                
            result_bool = result_bool and event_result_bool
            
        return result_bool
        
    except Exception:
        # Return None on any unexpected errors to trigger backoff to the zero-shot LLM fallback
        return None
