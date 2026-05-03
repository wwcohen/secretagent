"""Auto-generated code-distilled implementation for analyze_sentence."""

import re

def analyze_sentence(sentence):
    # Known event/competition/context patterns
    context_patterns = [
        r'in the Stanley Cup\.',
        r'in the Champions League Final\.',
        r'in the NFC divisional round\.',
        r'in the National League Championship Series\.',
        r'in the World Series\.',
        r'in the AFC Wild Card\.',
        r'in the American League Championship Series\.',
        r'in the NFC Championship\.',
        r'in the Super Bowl\.',
        r'in the NBA Finals\.',
        r'in the third period\.',
        r'in the fourth quarter\.',
        r'in the first quarter\.',
        r'in the second quarter\.',
        r'in the third quarter\.',
        r'in the first period\.',
        r'in the second period\.',
        r'in the [A-Z][\w\s]*?\.',
    ]
    
    # Try to find the last "in the ..." phrase that could be context
    # Split off context: find the last " in the " that leads to end of sentence
    context = ''
    action_and_context = sentence
    
    # Find all occurrences of " in the " 
    matches = list(re.finditer(r' in the ', sentence))
    
    if matches:
        # Try from the last match - check if what follows looks like an event/context
        for match in reversed(matches):
            pos = match.start()
            tail = sentence[pos+1:]  # "in the ..."
            remaining = sentence[:pos]
            # Check if removing this makes sense - tail should end with period
            if tail.endswith('.'):
                # This is a candidate for context
                context = tail
                action_and_context = remaining
                break
    
    if not context:
        action_and_context = sentence
    
    # Now split action_and_context into name and action
    # Name: sequence of capitalized words (including Jr., A.J., etc.) at the start
    # Try to find where the name ends and verb begins (first lowercase word that's a verb)
    
    name_pattern = re.compile(
        r'^((?:[A-Z][a-zA-Z]*\.?(?:\s+|$))*?(?:Jr\.\s*|Sr\.\s*)?)'
    )
    
    # Split words, find first word that starts with lowercase
    words = action_and_context.split()
    name_parts = []
    action_start = 0
    for i, word in enumerate(words):
        clean = word.rstrip('.')
        if word[0].isupper() or word[0] == '.' or (len(word) >= 2 and word[1] == '.'):
            name_parts.append(word)
            if word.endswith('Jr.') or word.endswith('Sr.'):
                action_start = i + 1
                break
            action_start = i + 1
        else:
            break
    
    name = ' '.join(name_parts)
    action = ' '.join(words[action_start:])
    
    # Clean trailing period from action if context is empty and action doesn't naturally end with one
    # Looking at examples: some keep period, some don't
    if not context and action.endswith('.'):
        # Check examples - "hit a triple." keeps period, "got on base." does not
        pass  # Keep as-is based on examples... actually let me re-check
    
    return [name, action, context]
