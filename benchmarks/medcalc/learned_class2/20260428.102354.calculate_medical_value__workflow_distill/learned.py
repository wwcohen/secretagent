"""Auto-generated workflow-distilled implementation for calculate_medical_value.

Calls existing tools from ptools.
"""

from ptools import *

def calculate_medical_value(patient_note: str, question: str) -> float:
    """Calculate medical values by orchestrating available tools.
    
    Pipeline:
    1. Try the distilled workflow first (Python extraction + calculation, zero LLM cost)
    2. If that fails, use the pipeline workflow (LLM-backed extraction + Python calculation)
    3. If that fails, fall back to simulate_medical_value (pure LLM reasoning)
    """
    import math
    
    # First, try the pipeline workflow which uses LLM for extraction but Python for computation
    try:
        result = pipeline_workflow(patient_note, question)
        if result is not None and not (isinstance(result, float) and math.isnan(result)):
            return result
    except Exception:
        pass
    
    # Fall back to the distilled workflow (Python-first approach)
    try:
        result = distilled_workflow(patient_note, question)
        if result is not None and not (isinstance(result, float) and math.isnan(result)):
            return result
    except Exception:
        pass
    
    # Final fallback: pure LLM simulation
    try:
        result = simulate_medical_value(patient_note=patient_note, question=question)
        if result is not None:
            # Try to extract a numeric value from the result
            if isinstance(result, (int, float)):
                return float(result)
            if isinstance(result, str):
                # Try to parse the numeric value from the string
                import re
                # Look for numbers (possibly negative, with decimals)
                numbers = re.findall(r'-?\d+\.?\d*', result)
                if numbers:
                    return float(numbers[-1])
    except Exception:
        pass
    
    return None
