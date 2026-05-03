"""Auto-generated workflow-distilled implementation for tabmwp_solve.

Calls existing tools from ptools.
"""

from ptools import *

def tabmwp_solve(question: str, table: str, table_id: str, choices: list | None) -> str:
    """Solve a TabMWP task end-to-end by orchestrating existing tools."""
    
    # Try the broad_workflow first as it's a clean 2-step pipeline
    try:
        result = broad_workflow(question, table, table_id, choices)
        if result is not None and str(result).strip():
            return str(result).strip()
    except Exception:
        pass
    
    # Try the rich_workflow as a fallback (4-step with full context)
    try:
        result = rich_workflow(question, table, table_id, choices)
        if result is not None and str(result).strip():
            return str(result).strip()
    except Exception:
        pass
    
    # Try the in-context workflow
    try:
        result = incontext_workflow(question, table, table_id, choices)
        if result is not None and str(result).strip():
            return str(result).strip()
    except Exception:
        pass
    
    # Final fallback: use extract_and_compute + format_answer directly
    try:
        raw = extract_and_compute(question, table, choices)
        if raw is not None:
            formatted = format_answer(raw, choices)
            if formatted is not None and str(formatted).strip():
                return str(formatted).strip()
            # If formatting failed, try returning raw
            return str(raw).strip()
    except Exception:
        pass
    
    # Try compute_answer directly
    try:
        result = compute_answer(question, table, choices)
        if result is not None and str(result).strip():
            return str(result).strip()
    except Exception:
        pass
    
    # Return None to trigger fallback to pure-LLM zero-shot
    return None
