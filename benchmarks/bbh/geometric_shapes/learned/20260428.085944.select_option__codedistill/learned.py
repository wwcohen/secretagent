"""Auto-generated code-distilled implementation for select_option."""

def select_option(description, options):
    desc_lower = description.lower().strip()
    
    # Define synonyms/mappings: description terms -> option shape names
    synonyms = {
        'quadrilateral': 'kite',
        'line segment': 'line',
        'oval': 'ellipse',
        'parallelogram': 'rectangle',
        'square': 'rectangle',
        'rhombus': 'kite',
        'trapezoid': 'kite',
        'trapezium': 'kite',
        'semicircle': 'sector',
        'semi-circle': 'sector',
        'arc': 'sector',
    }
    
    option_names = {opt[1].lower(): opt[0] for opt in options}
    
    # First, try direct match: check if any option name appears in the description
    # Sort by length descending to match longest first (e.g., "heptagon" before "pentagon" substring issues)
    sorted_options = sorted(option_names.keys(), key=len, reverse=True)
    
    for shape_name in sorted_options:
        if shape_name in desc_lower:
            letter = option_names[shape_name]
            return f'({letter})'
    
    # Try synonym mappings
    for synonym, target in synonyms.items():
        if synonym in desc_lower:
            if target in option_names:
                letter = option_names[target]
                return f'({letter})'
    
    # Try matching by number of sides mentioned
    side_words = {
        'three': 'triangle', '3': 'triangle',
        'four': 'kite', '4': 'kite',
        'five': 'pentagon', '5': 'pentagon',
        'six': 'hexagon', '6': 'hexagon',
        'seven': 'heptagon', '7': 'heptagon',
        'eight': 'octagon', '8': 'octagon',
    }
    
    for word, target in side_words.items():
        if word in desc_lower and 'side' in desc_lower:
            if target in option_names:
                letter = option_names[target]
                return f'({letter})'
    
    return None
