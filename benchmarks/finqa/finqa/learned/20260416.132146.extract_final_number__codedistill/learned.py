"""Auto-generated code-distilled implementation for extract_final_number."""

import re

def extract_final_number(text: str) -> str:
    if text is None:
        return None
    
    text = text.strip()
    
    # If the text is simply a number (possibly negative, possibly with decimal, possibly with %), return it
    if re.match(r'^-?\d+\.?\d*%?$', text):
        return text
    
    # Check if it's a simple arithmetic expression like '414000 + 364000'
    simple_expr = re.match(r'^(-?\d+\.?\d*)\s*([+\-*/])\s*(-?\d+\.?\d*)$', text)
    if simple_expr:
        a = float(simple_expr.group(1))
        op = simple_expr.group(2)
        b = float(simple_expr.group(3))
        if op == '+':
            result = a + b
        elif op == '-':
            result = a - b
        elif op == '*':
            result = a * b
        elif op == '/':
            if b != 0:
                result = a / b
            else:
                return None
        # Format: if result is integer, return as int string
        if result == int(result):
            return str(int(result))
        else:
            return str(result)
    
    # For longer text, try to find the final number (possibly after '=' sign)
    # Look for pattern like "= <number>" at the end
    match = re.search(r'=\s*(-?\d+\.?\d*%?)\s*$', text)
    if match:
        return match.group(1)
    
    # Try to find the last number (with optional negative sign and percent) in the text
    matches = re.findall(r'-?\d+\.?\d*%?', text)
    if matches:
        return matches[-1]
    
    return None
