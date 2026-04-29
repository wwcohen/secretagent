"""Auto-generated code-distilled implementation for select_option."""

def select_option(description, options):
    """
    Given a shape description and a list of options [letter, shape_name],
    find the best matching option and return it formatted as '(letter)'.
    """
    description_lower = description.lower().strip()
    
    # Direct match: check if the description exactly matches an option's shape name
    for letter, shape_name in options:
        if description_lower == shape_name.lower():
            return f'({letter})'
    
    # Partial match: check if an option's shape name is contained in the description
    # or if the description contains the shape name
    for letter, shape_name in options:
        if shape_name.lower() in description_lower:
            return f'({letter})'
    
    # Reverse partial match: check if description is contained in an option's shape name
    for letter, shape_name in options:
        if description_lower in shape_name.lower():
            return f'({letter})'
    
    # Keyword-based matching for common descriptions
    keyword_map = {
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
    }
    
    for keyword, shape in keyword_map.items():
        if keyword in description_lower:
            for letter, shape_name in options:
                if shape_name.lower() == shape:
                    return f'({letter})'
    
    return None
