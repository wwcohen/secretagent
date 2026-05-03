"""Auto-generated code-distilled implementation for extract_index."""

import re

def extract_index(text, choices):
    if not text or not choices:
        return None
        
    max_idx = -1
    max_pos = -1
    
    # 1. Try to find the exact choice string
    # The language model usually outputs the chosen assignment at the very end of the text.
    # Therefore, the choice with the highest last occurrence index (rfind) is the final choice.
    for i, choice in enumerate(choices):
        pos = text.rfind(choice)
        if pos > max_pos:
            max_pos = pos
            max_idx = i
            
    if max_pos != -1:
        return max_idx
        
    # 2. If exact match fails, try with normalized whitespace and case-insensitive matching
    def normalize(s):
        return re.sub(r'\s+', ' ', s).strip().lower()
        
    norm_text = normalize(text)
    for i, choice in enumerate(choices):
        norm_choice = normalize(choice)
        pos = norm_text.rfind(norm_choice)
        if pos > max_pos:
            max_pos = pos
            max_idx = i
            
    if max_pos != -1:
        return max_idx
        
    # 3. Fallback logic: check for mentions of "Candidate X" or "Choice X" at the end of the text
    tail = text[-500:].lower()
    last_mention_idx = -1
    last_mention_pos = -1
    
    for i in range(len(choices)):
        # Look for "candidate 1", "choice 2", etc. (1-based index)
        pattern = r'\b(?:candidate|choice)\s*' + str(i + 1) + r'\b'
        matches = list(re.finditer(pattern, tail))
        if matches:
            # Get the position of the last occurrence
            pos = matches[-1].end()
            if pos > last_mention_pos:
                last_mention_pos = pos
                last_mention_idx = i
                
    if last_mention_pos != -1:
        return last_mention_idx
        
    return None
