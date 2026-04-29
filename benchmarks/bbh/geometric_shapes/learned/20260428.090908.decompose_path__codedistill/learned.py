"""Auto-generated code-distilled implementation for decompose_path."""

import re

def decompose_path(path_str):
    """Decompose an SVG path string into a list of individual commands with their coordinates."""
    if not path_str or not isinstance(path_str, str):
        return None
    
    # Split the path string by finding each command letter followed by its parameters
    # SVG path commands are single letters (M, L, C, Z, etc.) followed by coordinates
    parts = re.findall(r'[A-Za-z][^A-Za-z]*', path_str)
    
    if not parts:
        return None
    
    result = [part.strip() for part in parts]
    
    return result
