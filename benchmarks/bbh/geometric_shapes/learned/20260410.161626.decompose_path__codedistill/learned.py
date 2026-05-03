"""Auto-generated code-distilled implementation for decompose_path."""

import re

def decompose_path(path):
    if not path or not isinstance(path, str):
        return None
    
    # Split the path at command boundaries - find each command letter and its arguments
    # Commands we've seen: M, L, A
    # Split at positions where a command letter appears (preceded by space or start)
    
    # Use regex to find each command: a letter followed by everything until the next command letter
    # Pattern: find all occurrences of a letter followed by non-letter content
    parts = re.findall(r'[MLAHVCSQTZmlahvcsqtz][^MLAHVCSQTZmlahvcsqtz]*', path)
    
    if not parts:
        return None
    
    result = []
    for part in parts:
        stripped = part.strip()
        if stripped:
            result.append(stripped)
    
    return result
