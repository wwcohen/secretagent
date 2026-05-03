"""Auto-generated workflow-distilled implementation for calculate_medical_value.

Calls existing tools from ptools.
"""

from ptools import *

def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate medical values by orchestrating available tools.
    
    Pipeline:
    1. Try the distilled workflow (Python-first, zero LLM cost)
    2. If that fails, try the pipeline workflow (LLM-backed extraction + Python computation)
    3. If that fails, fall back to simulate_medical_value (pure LLM reasoning)
    """
    import math
    
    # Initialize react state if needed
    try:
        from ptools_common import _REACT_STATE
        _REACT_STATE['narrative'] = patient_note
    except (ImportError, Exception):
        pass
    
    def is_valid_result(result):
        """Check if a result is valid and usable."""
        if result is None:
            return False
        try:
            val = float(result)
            if math.isnan(val) or math.isinf(val):
                return False
            return True
        except (TypeError, ValueError):
            return False
    
    # Strategy 1: Try distilled workflow (Python extraction + calculation, cheapest)
    try:
        result = distilled_workflow(patient_note, question)
        if is_valid_result(result):
            return float(result)
    except Exception:
        pass
    
    # Strategy 2: Try pipeline workflow (LLM extraction + Python computation)
    try:
        result = pipeline_workflow(patient_note, question)
        if is_valid_result(result):
            return float(result)
    except Exception:
        pass
    
    # Strategy 3: Try the general workflow function
    try:
        result = workflow(patient_note, question)
        if is_valid_result(result):
            return float(result)
    except Exception:
        pass
    
    # Strategy 4: Try PoT workflow
    try:
        result = pot_workflow(patient_note, question)
        if is_valid_result(result):
            return float(result)
    except Exception:
        pass
    
    # Strategy 5: Try simulate_medical_value (pure LLM reasoning)
    try:
        result = simulate_medical_value(patient_note, question)
        if result is not None:
            # Result might be a dict or a number
            if isinstance(result, (int, float)):
                if is_valid_result(result):
                    return float(result)
            elif isinstance(result, dict):
                # Try common keys
                for key in ['result', 'value', 'answer', 'output', 'score']:
                    if key in result and is_valid_result(result[key]):
                        return float(result[key])
                # Try first numeric value
                for v in result.values():
                    if is_valid_result(v):
                        return float(v)
            elif isinstance(result, str):
                # Try to parse a number from the string
                import re
                # Look for a number (possibly negative, possibly decimal)
                numbers = re.findall(r'-?\d+\.?\d*', result)
                if numbers:
                    val = float(numbers[-1])
                    if is_valid_result(val):
                        return val
            else:
                try:
                    val = float(result)
                    if is_valid_result(val):
                        return val
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass
    
    # Strategy 6: Try pot_medical_value
    try:
        result = pot_medical_value(patient_note, question)
        if result is not None:
            if isinstance(result, (int, float)) and is_valid_result(result):
                return float(result)
            elif isinstance(result, str):
                import re
                numbers = re.findall(r'-?\d+\.?\d*', result)
                if numbers:
                    val = float(numbers[-1])
                    if is_valid_result(val):
                        return val
            else:
                try:
                    val = float(result)
                    if is_valid_result(val):
                        return val
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass
    
    # All strategies failed — return None to trigger fallback
    return None
