"""Auto-generated code-distilled implementation for extract_final_number."""

import re
import math

def extract_final_number(s):
    if s is None:
        return None
    
    s = s.strip()
    
    if not s:
        return None
    
    # Case 1: Simple number (possibly with % or negative sign)
    if re.match(r'^-?\d+(\.\d+)?%?$', s):
        return s
    
    # Case 2: Simple word answers like 'yes', 'no', etc.
    if re.match(r'^[a-zA-Z]+$', s.strip()):
        return s.strip()
    
    # Case 3: If it's a list, take the first element
    if isinstance(s, list):
        s = s[0]
    
    # Case 4: Try to find a formula line and evaluate it
    # Look for "Formula: ..." pattern
    formula_match = re.search(r'Formula:\s*(.+?)(?:\n|$)', s)
    if formula_match:
        expr = formula_match.group(1).strip()
        try:
            result = eval(expr, {"__builtins__": {}}, {"min": min, "max": max, "abs": abs, "sum": sum, "round": round, "math": math})
            if isinstance(result, float) and result == int(result) and '%' not in str(result):
                return str(int(result))
            return str(result)
        except:
            pass
    
    # Case 5: Try to evaluate the entire string as an expression
    try:
        result = eval(s, {"__builtins__": {}}, {"min": min, "max": max, "abs": abs, "sum": sum, "round": round, "math": math})
        if isinstance(result, float):
            if result == int(result):
                return str(int(result))
            return str(result)
        if isinstance(result, (int, bool)):
            return str(result)
        return str(result)
    except:
        pass
    
    # Case 6: Try to find the last number in the string (possibly with % or negative)
    numbers = re.findall(r'-?\d+(?:\.\d+)?%?', s)
    if numbers:
        return numbers[-1]
    
    # Case 7: Return the string itself if it's short and looks like an answer
    if len(s) < 50:
        return s
    
    return None


def extract_final_number(input_val):
    """Handle both string and list inputs."""
    if isinstance(input_val, list):
        if len(input_val) == 0:
            return None
        s = input_val[0] if len(input_val) == 1 else input_val[0]
    elif isinstance(input_val, str):
        s = input_val
    else:
        return None
    
    s = s.strip()
    if not s:
        return None
    
    # Simple number with optional % or negative
    if re.match(r'^-?\d+(\.\d+)?%?$', s):
        return s
    
    # Simple word answer
    if re.match(r'^[a-zA-Z\s]+$', s.strip()):
        return s.strip()
    
    # Look for Formula: pattern
    formula_match = re.search(r'Formula:\s*(.+?)(?:\n|$)', s)
    if formula_match:
        expr = formula_match.group(1).strip()
        try:
            safe = {"__builtins__": {}, "min": min, "max": max, "abs": abs, "sum": sum, "round": round}
            result = eval(expr, safe)
            if isinstance(result, float) and result == int(result):
                return str(int(result))
            return str(result)
        except:
            pass
    
    # Try evaluating as expression
    try:
        safe = {"__builtins__": {}, "min": min, "max": max, "abs": abs, "sum": sum, "round": round}
        result = eval(s, safe)
        if isinstance(result, float):
            if result == int(result):
                return str(int(result))
            return str(round(result, 10))
        return str(result)
    except:
        pass
    
    # Last number in string
    numbers = re.findall(r'-?\d+(?:\.\d+)?%?', s)
    if numbers:
        return numbers[-1]
    
    if len(s) < 100:
        return s
    
    return None
