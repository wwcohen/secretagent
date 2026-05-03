"""Auto-generated workflow-distilled implementation for answer_date_question.

Calls existing tools from ptools.
"""

from ptools import *

import re
from datetime import datetime, timedelta

def answer_date_question(question: str) -> str:
    """Solve a date reasoning question by extracting the date, applying the offset, and matching to options."""
    
    # Parse options from the question
    options = re.findall(r'\(([A-Z])\)\s*(\d{2}/\d{2}/\d{4})', question)
    if not options:
        # fallback to LLM
        result = zeroshot_answer_date_question(question)
        return extract_option_letter(result)
    
    # Use LLM to figure out the target date in MM/DD/YYYY
    # We'll ask for structured output: the final answer date
    target_date_str = find_date_from_sentence(question)
    
    # Try to parse the target date
    target_date = _parse_date(target_date_str)
    
    if target_date is None:
        # Fallback: use zeroshot
        result = zeroshot_answer_date_question(question)
        letter = extract_option_letter(result)
        if letter and len(letter) <= 3:
            return _normalize_letter(letter)
        return None
    
    # Find the closest option
    best_letter = None
    best_diff = None
    
    for letter, date_str in options:
        opt_date = _parse_date(date_str)
        if opt_date is None:
            continue
        diff = abs((opt_date - target_date).days)
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_letter = letter
    
    if best_letter is not None:
        return f'({best_letter})'
    
    return None


def _parse_date(date_str: str):
    """Try to parse a date string in various formats."""
    if date_str is None:
        return None
    
    # Clean up the string
    date_str = date_str.strip().strip("'\"")
    
    # Try MM/DD/YYYY
    formats = [
        '%m/%d/%Y',
        '%m/%d/%y', 
        '%Y-%m-%d',
        '%B %d, %Y',
        '%b %d, %Y',
        '%d %B %Y',
        '%d %b %Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    
    # Try to extract MM/DD/YYYY pattern from the string
    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', date_str)
    if match:
        try:
            return datetime.strptime(match.group(1), '%m/%d/%Y')
        except (ValueError, TypeError):
            pass
    
    return None


def _normalize_letter(s: str) -> str:
    """Ensure the letter is in (X) format."""
    if s is None:
        return None
    s = s.strip()
    # Extract just the letter
    match = re.search(r'\(?([A-Z])\)?', s)
    if match:
        return f'({match.group(1)})'
    return s
