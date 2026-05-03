"""Auto-generated workflow-distilled implementation for answer_finqa.

Calls existing tools from ptools.
"""

from ptools import *

import re
import json


def answer_finqa(problem: str) -> str:
    """Workflow for answering FinQA numerical reasoning questions.
    
    Uses a multi-step approach:
    1. Extract a reasoning plan with target, values, and formula via LLM
    2. Try to compute the formula using Python eval
    3. Fall back to LLM-based computation if needed
    """
    # Step 1: Get the reasoning plan from the LLM
    try:
        plan = call_extract_reasoning_plan(problem)
    except Exception:
        plan = None

    if plan:
        # Try to extract a formula from the plan and compute it
        result = _try_compute_from_plan(plan)
        if result is not None:
            return result

    # Step 2: If plan-based computation failed, try the hand-coded workflow
    try:
        result = answer_finqa_workflow(problem)
        if result is not None and str(result).strip() != "":
            return result
    except Exception:
        pass

    # Step 3: Fall back to zero-shot LLM answer
    try:
        raw = zeroshot_answer_finqa(problem)
        if raw is not None:
            cleaned = _extract_number_from_text(str(raw))
            if cleaned is not None:
                return str(cleaned)
            return str(raw)
    except Exception:
        pass

    return None


def _try_compute_from_plan(plan: str) -> str:
    """Try to extract a formula from the reasoning plan and compute it."""
    if plan is None:
        return None

    # Look for a formula line in the plan
    formula = None
    lines = plan.strip().split('\n')
    
    for line in lines:
        line_lower = line.lower().strip()
        # Look for lines containing "formula:" or "calculation:" or "compute:"
        if any(keyword in line_lower for keyword in ['formula:', 'calculation:', 'compute:', 'expression:']):
            # Extract the part after the colon
            for keyword in ['formula:', 'calculation:', 'compute:', 'expression:']:
                if keyword in line_lower:
                    idx = line_lower.index(keyword)
                    formula_candidate = line[idx + len(keyword):].strip()
                    if formula_candidate:
                        formula = formula_candidate
                        break
            if formula:
                break

    # Also try to find formula in the plan text using regex patterns
    if not formula:
        # Look for mathematical expressions
        patterns = [
            r'formula[:\s]*(.+?)(?:\n|$)',
            r'calculation[:\s]*(.+?)(?:\n|$)',
            r'compute[:\s]*(.+?)(?:\n|$)',
        ]
        for pat in patterns:
            m = re.search(pat, plan, re.IGNORECASE)
            if m:
                formula = m.group(1).strip()
                break

    if formula:
        # Clean up the formula - remove markdown, text artifacts
        formula = _clean_formula(formula)
        if formula:
            try:
                result = call_compute(formula)
                if result is not None and str(result).strip() != "":
                    num = _extract_number_from_text(str(result))
                    if num is not None:
                        return str(num)
                    return str(result)
            except Exception:
                pass

    # Try to extract numbers and formula differently - use the whole plan
    # with call_compute on any expression we can find
    expr_patterns = [
        r'=\s*([\d\.\-\+\*\/\(\)\s]+)',
        r'([\d\.\-]+\s*[\+\-\*\/]\s*[\d\.\-]+(?:\s*[\+\-\*\/]\s*[\d\.\-]+)*)',
    ]
    
    # Try computing expressions found in plan
    for pat in expr_patterns:
        matches = re.findall(pat, plan)
        for match in reversed(matches):  # Last match is often the final answer
            match = match.strip()
            if match and any(c.isdigit() for c in match):
                try:
                    result = call_compute(match)
                    if result is not None:
                        num = _extract_number_from_text(str(result))
                        if num is not None:
                            return str(num)
                except Exception:
                    continue

    # Try to find a final answer in the plan text
    answer_patterns = [
        r'(?:final\s+)?answer[:\s]*([+-]?\d+\.?\d*)',
        r'result[:\s]*([+-]?\d+\.?\d*)',
        r'=\s*([+-]?\d+\.?\d*)\s*$',
    ]
    for pat in answer_patterns:
        m = re.search(pat, plan, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1)

    return None


def _clean_formula(formula: str) -> str:
    """Clean a formula string for evaluation."""
    if not formula:
        return None
    
    # Remove common text artifacts
    formula = formula.strip()
    formula = formula.strip('`')
    formula = formula.strip()
    
    # Remove dollar signs used as currency markers but keep the numbers
    formula = re.sub(r'\$\s*', '', formula)
    
    # Remove commas in numbers
    formula = re.sub(r'(\d),(\d)', r'\1\2', formula)
    
    # Remove percentage signs (but note: user might mean /100)
    # We'll leave this for now and let the LLM handle percentages
    
    # Remove trailing text after the expression
    # Keep only math-like characters
    # Allow digits, operators, parentheses, dots, spaces, minus
    cleaned = re.match(r'^[\d\.\+\-\*\/\(\)\s]+', formula)
    if cleaned:
        return cleaned.group(0).strip()
    
    # If it still has some expression-like content, return as-is
    if any(op in formula for op in ['+', '-', '*', '/']):
        return formula
    
    return None


def _extract_number_from_text(text: str) -> float:
    """Extract a numeric value from text."""
    if text is None:
        return None
    
    text = str(text).strip()
    
    # Try direct float conversion first
    try:
        return float(text)
    except (ValueError, TypeError):
        pass
    
    # Remove commas
    text_clean = text.replace(',', '')
    try:
        return float(text_clean)
    except (ValueError, TypeError):
        pass
    
    # Try to find a number in the text (last number is often the answer)
    numbers = re.findall(r'[+-]?\d+\.?\d*', text)
    if numbers:
        try:
            return float(numbers[-1])
        except (ValueError, TypeError):
            pass
    
    return None
