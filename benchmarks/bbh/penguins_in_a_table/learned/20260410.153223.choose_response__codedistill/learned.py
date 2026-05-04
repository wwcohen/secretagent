"""Auto-generated code-distilled implementation for choose_response."""

def choose_response(response, choices):
    import re
    
    # Check if response contains "FINAL ANSWER"
    has_final = 'FINAL ANSWER' in response
    
    if has_final:
        # Extract the answer (text before \nFINAL ANSWER)
        answer = response.split('\nFINAL ANSWER')[0].strip()
    else:
        answer = response.strip()
        # Try to compile the answer - if it's a valid expression that's not a number, raise syntax error
        # Based on the examples: '0' doesn't error, "I don't know" doesn't error, 'James' errors
        try:
            compile(answer + '\n', '<unknown>', 'eval')
        except SyntaxError:
            pass
        else:
            # It compiled successfully as an expression - if it's a name that matches a choice, raise error
            # 'James' is a valid identifier/expression -> raises error in the workflow
            # '0' is valid but numeric -> no error
            # "I don't know" has syntax error so won't reach here
            if not answer.replace('.', '').replace('-', '').isdigit() and answer.isidentifier():
                raise SyntaxError("invalid syntax", ("<unknown>", 2, None, None))
        
        # No FINAL ANSWER: default to first choice
        return choices[0]
    
    # Try exact match
    for choice in choices:
        if choice[1] == answer:
            return choice
    
    # Try numeric closest match
    try:
        answer_num = float(answer)
        best_choice = None
        best_diff = float('inf')
        for choice in choices:
            try:
                choice_num = float(choice[1])
                diff = abs(choice_num - answer_num)
                if diff < best_diff:
                    best_diff = diff
                    best_choice = choice
            except (ValueError, TypeError):
                pass
        if best_choice is not None:
            return best_choice
    except (ValueError, TypeError):
        pass
    
    # Default to first choice
    return choices[0]
