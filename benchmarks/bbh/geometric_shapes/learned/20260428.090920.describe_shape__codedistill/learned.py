"""Auto-generated code-distilled implementation for describe_shape."""

def describe_shape(descriptions):
    # Count the number of "Draw a line" entries
    line_count = sum(1 for d in descriptions if d.startswith('Draw a line'))
    
    if line_count == 0:
        return None
    
    # Check if the shape is closed (last line ends at the starting point)
    # Extract the move-to point
    move_entry = None
    for d in descriptions:
        if d.startswith('Move to'):
            move_entry = d
            break
    
    # Extract last draw line's endpoint
    last_draw = None
    for d in descriptions:
        if d.startswith('Draw a line'):
            last_draw = d
    
    closed = False
    if move_entry and last_draw:
        import re
        move_match = re.search(r'Move to \(([^)]+)\)', move_entry)
        draw_match = re.search(r'to \(([^)]+)\)\s*$', last_draw)
        if move_match and draw_match:
            start_point = move_match.group(1).strip()
            end_point = draw_match.group(1).strip()
            # Compare as strings (they should match if closed)
            if start_point == end_point:
                closed = True
    
    if not closed and line_count == 1:
        return 'A line segment'
    
    if not closed:
        # Open path - could still be a line segment or something else
        if line_count == 1:
            return 'A line segment'
        # For open paths, we might not be able to determine shape confidently
        return None
    
    # Closed polygon - number of sides equals line_count
    shape_names = {
        3: 'triangle',
        4: 'quadrilateral',
        5: 'pentagon',
        6: 'hexagon',
        7: 'heptagon',
        8: 'octagon',
        9: 'nonagon',
        10: 'decagon',
    }
    
    return shape_names.get(line_count, None)
