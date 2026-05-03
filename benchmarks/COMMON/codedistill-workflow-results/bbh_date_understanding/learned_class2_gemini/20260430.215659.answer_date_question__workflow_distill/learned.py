"""Auto-generated workflow-distilled implementation for answer_date_question.

Calls existing tools from ptools.
"""

from ptools import *

def answer_date_question(input_str: str) -> str:
    try:
        # Extract multiple-choice options
        options = extract_options(input_str)
        if not options or not isinstance(options, list):
            return None
            
        # Extract background date facts
        facts = extract_date_facts(input_str)
        if facts is None or not isinstance(facts, list):
            return None
            
        # Extract the question
        question = extract_question(input_str)
        if not question or not isinstance(question, str):
            return None
            
        # Build up inferences contextually based on extracted facts
        inferences = []
        for i, fact in enumerate(facts):
            # Each fact sees only previously stated facts as context
            inference = make_inference(fact, facts[:i])
            if not inference:
                return None
            inferences.append(inference)
            
        # Synthesize an answer to the question using the derived inferences
        answer = answer_question(question, inferences)
        if not answer or not isinstance(answer, str):
            return None
            
        # Match the generated answer text to the correct option
        matched = match_option(answer, options)
        if not matched or not isinstance(matched, tuple) or len(matched) < 1:
            return None
            
        # Format the option letter as exactly matching the expected output format
        letter = matched[0]
        return f"({letter})"
        
    except Exception:
        # Fall back to zero-shot on any unexpected failures (e.g., malformed outputs)
        return None
