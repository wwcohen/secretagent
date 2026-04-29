"""Auto-generated code-distilled implementation for select_option."""

def select_option(description, options):
    desc_lower = description.lower()
    
    # Build a dict from option name to letter
    option_map = {opt[1].lower(): opt[0] for opt in options}
    
    # First, try direct/exact match with option names (longer names first to avoid partial matches)
    sorted_options = sorted(option_map.keys(), key=len, reverse=True)
    
    # Check for direct containment of option name in description
    matches = []
    for opt_name in sorted_options:
        if opt_name in desc_lower:
            matches.append(opt_name)
    
    if matches:
        # If we have matches, pick the longest (most specific) one
        best = matches[0]  # already sorted by length desc
        return f'({option_map[best]})'
    
    # Semantic mappings for when no direct match is found
    # Handle "quadrilateral" - not directly in options usually
    if 'quadrilateral' in desc_lower:
        # Check if "irregular" or "acute" suggests kite vs rectangle
        if 'irregular' in desc_lower or 'acute' in desc_lower:
            if 'kite' in option_map:
                return f'({option_map["kite"]})'
        # Default quadrilateral mappings
        if 'right angle' in desc_lower or 'right' in desc_lower:
            if 'rectangle' in option_map:
                return f'({option_map["rectangle"]})'
        # Plain "quadrilateral" -> rectangle
        if 'rectangle' in option_map:
            return f'({option_map["rectangle"]})'
        if 'kite' in option_map:
            return f'({option_map["kite"]})'
    
    # Handle "line segment" -> "line"
    if 'line' in desc_lower or 'segment' in desc_lower or 'open path' in desc_lower:
        if 'line' in option_map:
            return f'({option_map["line"]})'
    
    # Handle lens/oval -> ellipse
    if 'lens' in desc_lower or 'oval' in desc_lower:
        if 'ellipse' in option_map:
            return f'({option_map["ellipse"]})'
    
    # Handle "closed curve" or similar -> circle or ellipse
    if 'curve' in desc_lower or 'closed' in desc_lower:
        if 'circle' in option_map:
            return f'({option_map["circle"]})'
        if 'ellipse' in option_map:
            return f'({option_map["ellipse"]})'
    
    # Handle polygon side counts
    import re
    side_match = re.search(r'(\d+)[- ]sided', desc_lower)
    if side_match:
        sides = int(side_match.group(1))
        side_to_shape = {3: 'triangle', 4: 'kite', 5: 'pentagon', 6: 'hexagon', 
                         7: 'heptagon', 8: 'octagon'}
        if sides in side_to_shape and side_to_shape[sides] in option_map:
            return f'({option_map[side_to_shape[sides]]})'
    
    return None
