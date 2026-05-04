"""Auto-generated code-distilled implementation for select_option."""

def select_option(description, options):
    """
    Given a shape description and a list of [letter, shape_name] options,
    select the best matching option and return it formatted as '(letter)'.
    """
    description_lower = description.lower().strip()
    
    # Direct keyword matching: check if any option's shape name appears in the description
    # We also handle common variations like "line segment" -> "line"
    
    # Build a mapping of synonyms/variations to canonical option names
    synonyms = {
        'line segment': 'line',
        'line': 'line',
        'circle': 'circle',
        'triangle': 'triangle',
        'rectangle': 'rectangle',
        'square': 'rectangle',
        'pentagon': 'pentagon',
        'hexagon': 'hexagon',
        'heptagon': 'heptagon',
        'octagon': 'octagon',
        'kite': 'kite',
        'sector': 'sector',
        'ellipse': 'ellipse',
        'parallelogram': 'parallelogram',
        'trapezoid': 'trapezoid',
        'rhombus': 'rhombus',
        'semicircle': 'semicircle',
        'arc': 'arc',
        'star': 'star',
    }
    
    # Try to find a synonym match in the description
    matched_canonical = None
    best_match_len = 0
    
    for synonym, canonical in synonyms.items():
        if synonym in description_lower:
            if len(synonym) > best_match_len:
                best_match_len = len(synonym)
                matched_canonical = canonical
    
    if matched_canonical:
        for letter, shape_name in options:
            if shape_name.lower() == matched_canonical:
                return f'({letter})'
    
    # Fallback: check if any option's shape name appears directly in the description
    # Sort by length descending to prefer longer (more specific) matches
    sorted_options = sorted(options, key=lambda x: len(x[1]), reverse=True)
    for letter, shape_name in sorted_options:
        if shape_name.lower() in description_lower:
            return f'({letter})'
    
    # Second fallback: check if description words overlap with option names
    desc_words = set(description_lower.split())
    best_score = 0
    best_letter = None
    for letter, shape_name in options:
        shape_words = set(shape_name.lower().split())
        overlap = len(desc_words & shape_words)
        if overlap > best_score:
            best_score = overlap
            best_letter = letter
    
    if best_score > 0:
        return f'({best_letter})'
    
    return None
