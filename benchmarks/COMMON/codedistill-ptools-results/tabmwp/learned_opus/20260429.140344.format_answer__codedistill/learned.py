"""Auto-generated code-distilled implementation for format_answer."""

import re

def format_answer(answer, choices):
    if choices is None:
        # Clean up the answer: remove $, units like /pound, commas in some cases
        cleaned = answer.strip()
        cleaned = re.sub(r'^\$', '', cleaned)
        cleaned = re.sub(r'/\w+$', '', cleaned)
        return cleaned
    
    # Check if answer is already in choices (exact match)
    if answer in choices:
        return answer
    
    # For binary choices like ['yes', 'no']
    if choices == ['yes', 'no']:
        if 'greater' in answer or 'more' in answer:
            return 'yes'
        if '<' in answer or 'less' in answer or 'fewer' in answer:
            return 'no'
        try:
            val = float(answer.replace(',', ''))
            return 'yes' if val > 0 else 'no'
        except ValueError:
            pass
    
    if choices == ['shortage', 'surplus']:
        if 'greater' in answer or 'more' in answer:
            return 'surplus'
        if '<' in answer or 'less' in answer or 'fewer' in answer:
            return 'shortage'
        try:
            val = float(answer.replace(',', ''))
            return 'shortage' if val >= 0 else 'surplus'
        except ValueError:
            pass
    
    # Try numeric index mapping (1-indexed)
    try:
        idx = int(answer.replace(',', '')) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    except (ValueError, IndexError):
        pass
    
    # Try to find a choice that appears in the answer
    for choice in choices:
        if choice.lower() in answer.lower():
            return choice
    
    return None
