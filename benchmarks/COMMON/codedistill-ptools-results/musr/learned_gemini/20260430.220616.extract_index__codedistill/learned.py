"""Auto-generated code-distilled implementation for extract_index."""

def extract_index(target, candidates):
    """
    Returns the index of the target in the candidates list.
    Returns None if the input cannot be handled confidently or if no match is found.
    """
    if not isinstance(candidates, list):
        return None

    # 1. Exact match
    if target in candidates:
        return candidates.index(target)

    # 2. Case-insensitive and stripped match
    if isinstance(target, str):
        target_clean = target.strip().lower()
        
        for i, candidate in enumerate(candidates):
            if isinstance(candidate, str) and candidate.strip().lower() == target_clean:
                return i
                
        # 3. Substring match as a fallback
        for i, candidate in enumerate(candidates):
            if isinstance(candidate, str):
                candidate_clean = candidate.strip().lower()
                if target_clean in candidate_clean or candidate_clean in target_clean:
                    return i

    return None
