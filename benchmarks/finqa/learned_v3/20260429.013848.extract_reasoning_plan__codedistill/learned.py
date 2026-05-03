"""Auto-generated code-distilled implementation for extract_reasoning_plan."""

import re

def extract_reasoning_plan(text):
    if not text or not isinstance(text, str):
        return None
    
    # Try to find an explicit answer pattern near the end of the text
    # Look for "the answer is" pattern
    answer_match = re.search(r'(?:the answer is|answer\s*[:=])\s*([^\n.]+)', text, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).strip()
    
    # Look for "Target/Values/Formula" plan format
    plan_match = re.search(r'(Target:.*?Formula:.*?)(?:\n\n|\Z)', text, re.DOTALL)
    if plan_match:
        return plan_match.group(1).strip()
    
    # Look for a final numerical result after "=" at the end
    eq_match = re.search(r'=\s*([+-]?\d+\.?\d*%?)\s*$', text.strip())
    if eq_match:
        return eq_match.group(1).strip()
    
    # Try to find the last line that looks like a standalone answer
    lines = text.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        # Check if line is just a number/percentage
        if re.match(r'^[+-]?\d+\.?\d*%?$', line):
            return line
        # Check for "answer: X" pattern
        m = re.match(r'(?:answer|result|final)\s*[:=]\s*(.+)', line, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        break
    
    # Search for the last number after common answer indicators
    patterns = [
        r'(?:therefore|thus|so|hence)[,\s]+(?:the\s+)?(?:answer\s+is\s+)?([+-]?\d+\.?\d*%?)',
        r'(?:equals?|is)\s+([+-]?\d+\.?\d*%?)\s*$',
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            return matches[-1].strip()
    
    # Try to get the last number/percentage in the text after the question
    q_match = re.search(r'\?\s*\n', text)
    if q_match:
        after_q = text[q_match.end():]
        nums = re.findall(r'[+-]?\d+\.?\d*%?', after_q)
        if nums:
            return nums[-1]
    
    # Fallback: find last number in text
    nums = re.findall(r'[+-]?\d+\.?\d*%?', text)
    if nums:
        return nums[-1]
    
    return None
