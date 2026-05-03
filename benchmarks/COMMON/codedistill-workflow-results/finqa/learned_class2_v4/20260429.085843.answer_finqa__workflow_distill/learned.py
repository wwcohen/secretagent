"""Auto-generated workflow-distilled implementation for answer_finqa.

Calls existing tools from ptools.
"""

from ptools import *

def answer_finqa(problem: str) -> str:
    """Solve a FinQA numerical reasoning question by extracting a reasoning plan,
    then computing the result. Falls back to None if anything goes wrong."""
    import re
    
    # Step 1: Try the structured workflow first
    try:
        # Extract reasoning plan with target, values, and formula
        plan_text = call_extract_reasoning_plan(problem)
        
        if plan_text is None:
            return None
        
        # Try to find a formula in the plan
        formula = None
        
        # Look for formula patterns in the plan text
        formula_patterns = [
            r'[Ff]ormula[:\s]*(.+?)(?:\n|$)',
            r'[Cc]alculation[:\s]*(.+?)(?:\n|$)',
            r'[Ee]xpression[:\s]*(.+?)(?:\n|$)',
            r'[Cc]ompute[:\s]*(.+?)(?:\n|$)',
        ]
        
        for pat in formula_patterns:
            m = re.search(pat, plan_text)
            if m:
                formula = m.group(1).strip()
                break
        
        # Try to compute if we found a formula
        if formula:
            try:
                result = call_compute(formula)
                if result is not None:
                    # Try to parse the result as a number
                    result_str = str(result).strip()
                    # Remove any trailing text after the number
                    num_match = re.search(r'^[-+]?\d*\.?\d+', result_str)
                    if num_match:
                        num_val = float(num_match.group())
                        # Format the result properly
                        if num_val == int(num_val) and '.' not in num_match.group():
                            return str(int(num_val))
                        else:
                            # Round to 5 decimal places to match expected output format
                            rounded = round(num_val, 5)
                            if rounded == int(rounded):
                                return str(round(num_val, 1)) if abs(num_val - int(num_val)) > 0.001 else str(int(rounded)) + ".0"
                            return str(rounded)
            except Exception:
                pass
        
        # If structured extraction didn't yield a computable formula,
        # try the full workflow approach
        result = answer_finqa_workflow(problem)
        if result is not None:
            result_str = str(result).strip()
            # Validate it looks like a number
            num_match = re.search(r'^[-+]?\d*\.?\d+', result_str)
            if num_match:
                return result_str
        
        # Try zero-shot as another approach
        raw = zeroshot_answer_finqa(problem)
        if raw is not None:
            raw_str = str(raw).strip()
            # Try to extract a number from the response
            cleaned = extract_final_number(raw_str)
            if cleaned is not None:
                cleaned_str = str(cleaned).strip()
                num_match = re.search(r'[-+]?\d*\.?\d+', cleaned_str)
                if num_match:
                    return cleaned_str
            # Try direct number extraction from raw
            num_match = re.search(r'[-+]?\d*\.?\d+', raw_str)
            if num_match:
                return num_match.group()
        
        return None
        
    except Exception:
        # If anything fails, try the simpler approaches
        try:
            result = answer_finqa_workflow(problem)
            if result is not None:
                result_str = str(result).strip()
                num_match = re.search(r'[-+]?\d*\.?\d+', result_str)
                if num_match:
                    return result_str
        except Exception:
            pass
        
        try:
            raw = zeroshot_answer_finqa(problem)
            if raw is not None:
                cleaned = extract_final_number(str(raw))
                if cleaned is not None:
                    return str(cleaned).strip()
        except Exception:
            pass
        
        return None
