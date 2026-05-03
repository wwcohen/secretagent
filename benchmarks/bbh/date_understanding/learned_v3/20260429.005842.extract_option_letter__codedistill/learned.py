"""Auto-generated code-distilled implementation for extract_option_letter."""

import re


def extract_option_letter(text):
    """
    Extract a single option letter (A, B, C, D, etc.) from a text string
    that represents a multiple-choice answer selection.
    
    Returns None if the input cannot be handled confidently.
    """
    if text is None:
        return None
    
    if not isinstance(text, str):
        return None
    
    text = text.strip()
    
    if not text:
        return None
    
    # If it's just a single letter (possibly with whitespace)
    if re.fullmatch(r'[A-Za-z]', text):
        return text.upper()
    
    # Pattern: (A) or (a)
    match = re.fullmatch(r'\(([A-Za-z])\)', text)
    if match:
        return match.group(1).upper()
    
    # Pattern: A) or a)
    match = re.fullmatch(r'([A-Za-z])\)', text)
    if match:
        return match.group(1).upper()
    
    # Pattern: A. or a.
    match = re.fullmatch(r'([A-Za-z])\.', text)
    if match:
        return match.group(1).upper()
    
    # Pattern: "The answer is A" / "The answer is (A)" / "The correct answer is A"
    match = re.search(r'(?:the\s+)?(?:correct\s+)?answer\s+is\s*[:\s]*\(?([A-Za-z])\)?\.?\s*$', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Pattern: "Option A" / "option A"
    match = re.search(r'option\s+\(?([A-Za-z])\)?\.?\s*$', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Pattern: starts with a letter followed by punctuation/separator then description
    # e.g., "A. Some description" or "A) Some description" or "(A) Some description"
    match = re.match(r'\(?([A-Za-z])\)?[\.\)\:\s]\s*\S', text)
    if match:
        letter = match.group(1).upper()
        # Only confident if it's a typical option letter (A-F range)
        if letter in 'ABCDEF':
            return letter
    
    # Pattern: text ends with a single letter that looks like an answer
    # e.g., "I would choose A"
    match = re.search(r'(?:choose|select|pick|go with|is)\s+\(?([A-Za-z])\)?\.?\s*$', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Pattern: just a letter with some surrounding punctuation/whitespace
    match = re.fullmatch(r'[\s\(\[\{]*([A-Za-z])[\s\)\]\}\.\,\:]*', text)
    if match:
        return match.group(1).upper()
    
    # Cannot confidently extract an option letter
    return None
