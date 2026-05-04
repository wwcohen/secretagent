"""Auto-generated code-distilled implementation for extract_option_letter."""

import re

def extract_option_letter(text: str):
    """Extract the option letter in parentheses from a string like '(A) 01/31/2012'."""
    match = re.match(r'\(([A-Z])\)', text.strip())
    if match:
        return match.group(0)
    return None
