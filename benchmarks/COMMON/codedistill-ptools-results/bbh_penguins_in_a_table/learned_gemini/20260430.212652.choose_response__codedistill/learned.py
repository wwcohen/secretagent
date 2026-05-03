"""Auto-generated code-distilled implementation for choose_response."""

def choose_response(answer, choices):
    # 1. Check for an exact string match (ignoring leading/trailing spaces)
    for choice in choices:
        if answer.strip() == choice[1].strip():
            return choice

    # 2. Check for a case-insensitive match
    for choice in choices:
        if answer.strip().lower() == choice[1].strip().lower():
            return choice

    # 3. Check for the closest numerical value if the answer is a number
    try:
        ans_num = float(answer.replace(',', '').strip())
        closest_choice = None
        min_diff = float('inf')
        
        for choice in choices:
            try:
                choice_num = float(choice[1].replace(',', '').strip())
                diff = abs(ans_num - choice_num)
                if diff < min_diff:
                    min_diff = diff
                    closest_choice = choice
            except ValueError:
                continue
                
        if closest_choice is not None:
            return closest_choice
    except ValueError:
        pass

    # 4. Check for partial text matches as a fallback
    for choice in choices:
        if answer.strip().lower() in choice[1].lower() or choice[1].strip().lower() in answer.lower():
            return choice

    return None
