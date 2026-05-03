"""Auto-generated code-distilled implementation for extract_path_and_options."""

import re

def extract_path_and_options(text):
    # Extract the SVG path data from the d="..." attribute
    path_match = re.search(r'<path d="([^"]+)"', text)
    if not path_match:
        return None
    
    path_data = path_match.group(1)
    
    # Extract the options section
    options_match = re.search(r'Options:\n(.*)', text, re.DOTALL)
    if not options_match:
        return None
    
    options_text = options_match.group(1)
    
    # Parse individual options like (A) circle, (B) heptagon, etc.
    option_pattern = re.findall(r'\(([A-Z])\)\s+(\w+)', options_text)
    if not option_pattern:
        return None
    
    options = [[letter, name] for letter, name in option_pattern]
    
    return [path_data, options]
