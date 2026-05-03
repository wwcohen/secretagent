"""Auto-generated code-distilled implementation for decompose_path."""

import re

def decompose_path(path):
    if not path or not isinstance(path, str):
        return None
    
    # Split the path at command letters (M, L, A, C, S, Q, T, H, V, Z, and lowercase variants)
    # We want to split right before each command letter
    # Use regex to find each command and its parameters
    parts = re.findall(r'[MLHVCSQTAZmlhvcsqtaz][^MLHVCSQTAZmlhvcsqtaz]*', path)
    
    if not parts:
        return None
    
    result = [part.strip() for part in parts]
    
    return result
