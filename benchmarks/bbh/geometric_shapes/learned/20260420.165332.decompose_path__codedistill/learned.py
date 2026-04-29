"""Auto-generated code-distilled implementation for decompose_path."""

import re

def decompose_path(path):
    if not path or not isinstance(path, str):
        return None
    
    # Split the path string at each command letter (M, L, A, etc.) while keeping the delimiter
    # We need to find each command and its associated parameters
    parts = re.split(r'(?=[MmLlHhVvCcSsQqTtAaZz])', path.strip())
    
    result = []
    for part in parts:
        part = part.strip()
        if part:
            result.append(part)
    
    return result if result else None
