"""Auto-generated code-distilled implementation for choose_response."""

import re
import math

def choose_response(response, options):
    # 1. Exact match
    for option in options:
        if response == option[1]:
            return option
    
    # 2. Check if an option value is a substring of the response
    # or the response contains the option value as a word/number
    substring_matches = []
    for option in options:
        if option[1] in response:
            substring_matches.append(option)
    if len(substring_matches) == 1:
        return substring_matches[0]
    if len(substring_matches) > 1:
        # Pick the longest match
        best = max(substring_matches, key=lambda o: len(o[1]))
        return best
    
    # 3. Try numeric matching
    # Extract numbers from response
    response_numbers = re.findall(r'[-+]?\d*\.?\d+', response)
    if response_numbers:
        resp_val = float(response_numbers[0])
        numeric_options = []
        for option in options:
            try:
                opt_val = float(option[1])
                numeric_options.append((option, opt_val))
            except (ValueError, TypeError):
                pass
        if numeric_options:
            closest = min(numeric_options, key=lambda x: abs(x[1] - resp_val))
            return closest[0]
    
    # 4. Check if response contains any option value (case-insensitive)
    response_lower = response.lower()
    for option in options:
        if option[1].lower() in response_lower:
            return option
    
    # 5. Try to find option value words in response
    for option in options:
        # Check if any word in option value appears in response
        option_words = set(option[1].lower().split())
        response_words = set(response_lower.split())
        if option_words & response_words:
            return option
    
    # 6. Fallback: check by letter reference (e.g., response contains 'A', 'B', etc.)
    response_upper = response.upper().strip()
    for option in options:
        if option[0] == response_upper:
            return option
    
    # 7. Last resort: return the first option (closest default)
    # Based on the 'Cannot determine gender' example -> returns Gwen (the unique/outlier)
    # This is a very specific heuristic; return first option as default
    if options:
        return options[0]
    
    return None
