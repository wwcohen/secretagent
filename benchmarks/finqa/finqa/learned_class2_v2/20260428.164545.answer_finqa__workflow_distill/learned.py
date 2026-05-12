"""Auto-generated workflow-distilled implementation for answer_finqa.

Calls existing tools from ptools.
"""

from ptools import *

import re
import json


def answer_finqa(problem: str) -> str:
    """Solve a FinQA numerical reasoning question over a financial report excerpt.
    
    Uses a multi-step approach:
    1. Extract a reasoning plan with target, values, and formula via LLM
    2. Evaluate the formula using Python arithmetic
    3. Fall back to direct LLM answer if needed
    """
    # Step 1: Try the hand-coded workflow first (it already orchestrates extract + compute)
    try:
        result = answer_finqa_workflow(problem)
        if result is not None and str(result).strip() not in ('', 'None', 'none', 'N/A'):
            return result
    except Exception:
        pass
    
    # Step 2: If workflow failed, try extracting reasoning plan and computing manually
    try:
        plan_text = call_extract_reasoning_plan(problem)
        
        if plan_text:
            # Try to find a formula in the plan
            formula_match = re.search(r'[Ff]ormula[:\s]*(.+?)(?:\n|$)', plan_text)
            if formula_match:
                formula = formula_match.group(1).strip()
                # Try to find values and substitute them
                # Look for value definitions like "X = 123"
                value_defs = re.findall(r'(\w+)\s*=\s*([\d.,\-]+)', plan_text)
                for var_name, var_val in value_defs:
                    formula = formula.replace(var_name, var_val.replace(',', ''))
                
                # Try computing the formula
                try:
                    compute_result = call_compute(formula)
                    if compute_result and compute_result.strip() not in ('', 'None', 'Error'):
                        return compute_result.strip()
                except Exception:
                    pass
            
            # Try to find any arithmetic expression in the plan
            expressions = re.findall(r'(?:=\s*)([\d.,\s\+\-\*/\(\)%]+)', plan_text)
            for expr in reversed(expressions):  # last expression is usually the answer
                expr_clean = expr.strip().replace(',', '').strip()
                if expr_clean and any(c.isdigit() for c in expr_clean):
                    try:
                        compute_result = call_compute(expr_clean)
                        if compute_result and compute_result.strip() not in ('', 'None', 'Error'):
                            return compute_result.strip()
                    except Exception:
                        continue
    except Exception:
        pass
    
    # Step 3: Fall back to zero-shot LLM answer
    try:
        raw_answer = zeroshot_answer_finqa(problem)
        if raw_answer:
            # Clean up the answer
            cleaned = coerce_to_answer(raw_answer)
            if cleaned is not None and str(cleaned).strip() not in ('', 'None', 'none'):
                return str(cleaned).strip()
            
            # Try to extract a number from the raw answer
            result = extract_final_number(raw_answer)
            if result is not None and str(result).strip() not in ('', 'None', 'none'):
                return str(result).strip()
    except Exception:
        pass
    
    # Step 4: Last resort - try unstructured baseline
    try:
        result = unstructured_baseline_workflow(problem)
        if result is not None and str(result).strip() not in ('', 'None', 'none'):
            return result
    except Exception:
        pass
    
    return None
