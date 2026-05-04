"""Auto-generated code-distilled implementation for extract_index."""

def extract_index(text, choices):
    import re
    
    # First, try direct exact substring match
    matches = []
    for i, choice in enumerate(choices):
        if choice in text:
            matches.append(i)
    
    # If exactly one match, return it
    if len(matches) == 1:
        return matches[0]
    
    # If the text itself equals one of the choices
    for i, choice in enumerate(choices):
        if text.strip() == choice.strip():
            return i
    
    # For longer texts (reasoning/evaluation), we need to find which choice is selected.
    # Strategy: find all occurrences of each choice in the text, and also look for 
    # indicators like "VALID", "best", "optimal", "final answer", "selected" near them.
    
    # Try to find the answer at the end of the text or after key phrases
    # Look for patterns like "final answer", "best assignment", "optimal", "selected", "VALID"
    
    # Check for the last occurrence approach - often the final answer is restated at the end
    # Look at the last portion of the text
    last_portion = text[-500:] if len(text) > 500 else text
    
    # Check which choices appear in the last portion
    last_matches = []
    for i, choice in enumerate(choices):
        if choice in last_portion:
            last_matches.append(i)
    
    if len(last_matches) == 1:
        return last_matches[0]
    
    # Try to find "Candidate N" or "Choice N" marked as VALID or best/optimal/final
    # Search for patterns indicating the chosen candidate
    valid_pattern = re.findall(r'(?:Candidate|Choice)\s+(\d+)[^.]*?(?:VALID|valid|best|optimal|selected|final)', text)
    if valid_pattern:
        # Take the last mentioned valid candidate
        idx = int(valid_pattern[-1]) - 1
        if 0 <= idx < len(choices):
            return idx
    
    # Look for "The best/optimal/final assignment is Candidate/Choice N"
    final_patterns = re.findall(r'(?:best|optimal|final|selected|choose|chosen|answer)[^.]*?(?:Candidate|Choice)\s+(\d+)', text, re.IGNORECASE)
    if final_patterns:
        idx = int(final_patterns[-1]) - 1
        if 0 <= idx < len(choices):
            return idx
    
    # Look for "Candidate N" as the answer near end
    candidate_refs = re.findall(r'(?:Candidate|Choice)\s+(\d+)', last_portion)
    if candidate_refs:
        idx = int(candidate_refs[-1]) - 1
        if 0 <= idx < len(choices):
            return idx

    # If we have multiple matches, try finding which one is closest to end of text
    if len(matches) > 1:
        best_idx = -1
        best_pos = -1
        for i in matches:
            pos = text.rfind(choices[i])
            if pos > best_pos:
                best_pos = pos
                best_idx = i
        if best_idx >= 0:
            return best_idx
    
    # If we have matches at all, return the last one found
    if matches:
        best_idx = -1
        best_pos = -1
        for i in matches:
            pos = text.rfind(choices[i])
            if pos > best_pos:
                best_pos = pos
                best_idx = i
        return best_idx
    
    return None
