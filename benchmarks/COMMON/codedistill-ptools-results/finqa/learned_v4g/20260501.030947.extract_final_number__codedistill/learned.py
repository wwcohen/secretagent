"""Auto-generated code-distilled implementation for extract_final_number."""

import re
import math

def extract_final_number(text):
    if not isinstance(text, str):
        return None
        
    # FinQA and TAT-QA logic typically places the final expression after "Formula:"
    parts = re.split(r'(?i)formula\s*:', text)
    expr = parts[-1].strip()
    
    # Check if the extracted expression is directly a number
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    # If it's directly a float or integer string, return as is to preserve exact formatting
    if is_number(expr):
        return expr
        
    # Build a safe environment for mathematical evaluation
    safe_env = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
    safe_env['min'] = min
    safe_env['max'] = max
    safe_env['abs'] = abs
    safe_env['round'] = round

    try:
        # Try evaluating the math expression
        result = eval(expr, {"__builtins__": None}, safe_env)
        
        # Ensure that the result is strictly a number and not a boolean or other types
        if isinstance(result, (int, float)) and not isinstance(result, bool):
            return str(result)
    except Exception:
        # Fallback if evaluation throws SyntaxError, NameError, etc. (e.g. percentages, strings like "yes")
        pass
        
    return expr
