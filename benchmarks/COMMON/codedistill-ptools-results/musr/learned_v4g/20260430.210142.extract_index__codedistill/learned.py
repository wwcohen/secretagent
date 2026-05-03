"""Auto-generated code-distilled implementation for extract_index."""

def extract_index(target: str, options: list):
    """
    Returns the index of the target in the options list.
    Returns None if the target is not found or input is invalid.
    """
    if not isinstance(options, list):
        return None
        
    try:
        return options.index(target)
    except ValueError:
        pass
        
    # Fallback to case-insensitive and stripped matching if exact match fails
    if isinstance(target, str):
        target_clean = target.strip().lower()
        for i, option in enumerate(options):
            if isinstance(option, str) and option.strip().lower() == target_clean:
                return i
                
    return None
