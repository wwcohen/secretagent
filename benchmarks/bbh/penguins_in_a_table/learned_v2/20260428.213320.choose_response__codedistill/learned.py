"""Auto-generated code-distilled implementation for choose_response."""

def choose_response(response, choices):
    # First, try exact match
    for choice in choices:
        if choice[1] == response:
            return choice
    
    # Try numeric comparison for cases like '48.0' matching '60' (closest match)
    try:
        response_num = float(response)
        # Find the closest numeric match
        best_choice = None
        best_diff = float('inf')
        for choice in choices:
            try:
                choice_num = float(choice[1])
                diff = abs(choice_num - response_num)
                if diff < best_diff:
                    best_diff = diff
                    best_choice = choice
            except (ValueError, TypeError):
                continue
        if best_choice is not None:
            return best_choice
    except (ValueError, TypeError):
        pass
    
    # If no match found, return None
    return None
