"""Auto-generated workflow-distilled implementation for answer_question_workflow.

Calls existing tools from ptools_murder.
"""

from ptools_murder import *

def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    from ptools_common import _REACT_STATE
    _REACT_STATE['narrative'] = narrative

    # Step 1: Extract suspects, means, and motives from the narrative
    evidence = ""
    try:
        res_evidence = extract_suspects_and_evidence(narrative)
        if res_evidence:
            evidence = str(res_evidence)
    except Exception:
        pass

    # Step 2: Extract and verify opportunities/alibis
    alibis = ""
    try:
        res_alibis = verify_alibis(narrative)
        if res_alibis:
            alibis = str(res_alibis)
    except Exception:
        # Fallback if verify_alibis expects the extracted evidence as context
        try:
            res_alibis = verify_alibis(narrative, evidence)
            if res_alibis:
                alibis = str(res_alibis)
        except Exception:
            pass

    # Step 3: Deduce the murderer using the decomposed evidence and alibis
    ans_str = None
    try:
        res_deduce = deduce_murderer(narrative, evidence, alibis, question, choices)
        if res_deduce:
            ans_str = str(res_deduce)
    except Exception:
        pass

    # Fallback 1: deduce_murderer without explicit decomposed string inputs
    if not ans_str:
        try:
            res_deduce = deduce_murderer(narrative, question, choices)
            if res_deduce:
                ans_str = str(res_deduce)
        except Exception:
            pass

    # Fallback 2: General purpose raw_answer 
    if not ans_str:
        try:
            res_raw = raw_answer(narrative, question, choices)
            if res_raw:
                ans_str = str(res_raw)
        except Exception:
            pass

    # Fallback 3: Single-ptool answer_question (which may return an int directly)
    if not ans_str:
        try:
            res_aq = answer_question(narrative, question, choices)
            if isinstance(res_aq, int):
                return res_aq
            elif res_aq is not None:
                ans_str = str(res_aq)
        except Exception:
            pass

    # If all generation attempts failed, return None
    if not ans_str:
        return None

    # Step 4: Extract the choice index from the textual reasoning/answer
    try:
        idx = extract_index(ans_str, choices)
        return int(idx)
    except (ValueError, TypeError, Exception):
        return None
