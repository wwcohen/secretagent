"""Auto-generated code-distilled implementation for extract_path_and_options."""

import re

def extract_path_and_options(text):
    try:
        # Extract the path data from the d="..." attribute
        path_match = re.search(r'd="([^"]*)"', text)
        if not path_match:
            return None
        path_data = path_match.group(1)
        
        # Extract options - find the Options: section and parse each option
        options_match = re.search(r'Options:\n(.*)', text, re.DOTALL)
        if not options_match:
            return None
        
        options_text = options_match.group(1)
        # Match patterns like (A) circle, (B) heptagon, etc.
        option_matches = re.findall(r'\(([A-Z])\)\s+(\w+)', options_text)
        if not option_matches:
            return None
        
        options = [[letter, shape] for letter, shape in option_matches]
        
        return [path_data, options]
    except Exception:
        return None
