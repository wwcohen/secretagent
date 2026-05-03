"""Auto-generated code-distilled implementation for extract_final_number."""

import re

def extract_final_number(text: str) -> str:
    if text is None:
        return None
    
    text = text.strip()
    
    # Pattern to match numbers: optional negative sign, digits with optional decimal, optional %
    # Also handle numbers prefixed with $ or other currency symbols
    pattern = r'-?\d+(?:\.\d+)?%?'
    
    matches = re.findall(pattern, text)
    
    if not matches:
        return None
    
    # Return the last match
    return matches[-1]
