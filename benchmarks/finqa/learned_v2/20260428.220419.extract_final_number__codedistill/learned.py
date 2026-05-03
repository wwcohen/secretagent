"""Auto-generated code-distilled implementation for extract_final_number."""

import re

def extract_final_number(s: str) -> str:
    if s is None:
        return None
    
    s = s.strip()
    
    # Pattern to match a number: optional negative sign, digits with optional decimal point, optional % suffix
    # We also want to handle numbers prefixed with $ or other currency symbols
    number_pattern = r'-?\d+(?:\.\d+)?%?'
    
    # First, check if the entire string is just a number (with optional %)
    full_match = re.fullmatch(r'-?\d+(?:\.\d+)?%?', s)
    if full_match:
        return s
    
    # Otherwise, find the last number in the string
    # We look for numbers that could be preceded by = sign, spaces, $, etc.
    matches = re.findall(number_pattern, s)
    
    if matches:
        return matches[-1]
    
    return None
