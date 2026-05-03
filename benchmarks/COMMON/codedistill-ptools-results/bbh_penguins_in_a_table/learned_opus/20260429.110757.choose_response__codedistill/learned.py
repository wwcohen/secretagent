"""Auto-generated code-distilled implementation for choose_response."""

def choose_response(answer, responses):
    # First, check for exact string match
    for response in responses:
        if response[1] == answer:
            return response
    
    # If no exact match, try numeric closest match
    try:
        answer_num = float(answer)
    except (ValueError, TypeError):
        return None
    
    best_response = None
    best_distance = float('inf')
    
    for response in responses:
        try:
            val_num = float(response[1])
        except (ValueError, TypeError):
            continue
        
        distance = abs(answer_num - val_num)
        if distance < best_distance:
            best_distance = distance
            best_response = response
    
    if best_response is not None:
        return best_response
    
    return None
