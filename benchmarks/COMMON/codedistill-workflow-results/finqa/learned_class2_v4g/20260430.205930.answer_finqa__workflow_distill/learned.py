"""Auto-generated workflow-distilled implementation for answer_finqa.

Calls existing tools from ptools.
"""

from ptools import *

import re

def answer_finqa(problem: str) -> str:
    try:
        # Step 1: Extract the reasoning plan
        plan = call_extract_reasoning_plan(problem)
        
        if plan:
            # Step 2: Extract the formula from the plan
            formula_match = re.search(r'(?i)formula\s*:\s*([^\n]+)', plan)
            if formula_match:
                formula = formula_match.group(1)
                
                # Take the part before '=' if the LLM provided an equation
                if '=' in formula:
                    formula = formula.split('=')[0]
                
                # Clean up to keep only valid mathematical characters
                formula = re.sub(r'[^0-9\.\+\-\*\/\(\)\s]', '', formula).strip()
                
                # Step 3: Evaluate the formula
                if formula:
                    try:
                        result = call_compute(formula)
                        if result is not None and str(result).strip():
                            return str(result).strip()
                    except Exception:
                        pass
            
            # Step 4: Fallback to LLM extraction if no clean formula is found/evaluated
            try:
                ans = extract_final_number(plan)
                if ans is not None and str(ans).strip():
                    return str(ans).strip()
            except Exception:
                pass
                
    except Exception:
        pass
        
    # Ultimate fallback: use the provided end-to-end workflow tool
    try:
        res = answer_finqa_workflow(problem)
        if res is not None and str(res).strip():
            return str(res).strip()
    except Exception:
        pass
        
    return None
