"""Auto-generated code-distilled implementation for decompose_path."""

import re

def decompose_path(path_string):
    """Decompose an SVG path string into a list of individual commands with their parameters."""
    if not path_string or not isinstance(path_string, str):
        return None
    
    # Match SVG path commands: a letter followed by optional coordinates/parameters
    # SVG commands are single letters: M, L, H, V, C, S, Q, T, A, Z (and lowercase variants)
    parts = re.split(r'(?=[A-Za-z])', path_string.strip())
    
    result = []
    for part in parts:
        part = part.strip()
        if part:
            result.append(part)
    
    if not result:
        return None
    
    return result
