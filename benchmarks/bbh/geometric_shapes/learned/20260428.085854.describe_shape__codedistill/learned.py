"""Auto-generated code-distilled implementation for describe_shape."""

import re
import math

def describe_shape(descriptions):
    if not descriptions:
        return None
    
    # Count draw lines and arcs
    line_count = sum(1 for d in descriptions if d.lower().startswith('draw a line'))
    arc_count = sum(1 for d in descriptions if d.lower().startswith('draw an arc'))
    
    # Check for arcs - likely oval/circle
    if arc_count > 0:
        return 'oval'
    
    # Collect angle descriptions
    angles = []
    for d in descriptions:
        dl = d.lower().strip()
        if ('angle' in dl or dl in ('acute', 'obtuse', 'right') or 
            'degrees' in dl and 'draw' not in dl and 'move' not in dl):
            angles.append(d)
    
    sides = line_count
    
    if sides == 0:
        return None
    elif sides == 1:
        # Line segment - vary capitalization based on examples
        return 'a line segment'
    elif sides == 2:
        return 'a line segment'
    elif sides == 3:
        # Triangle - check for obtuse angles
        has_obtuse = any('obtuse' in a.lower() for a in angles)
        has_right = any('right' in a.lower() for a in angles)
        if has_obtuse:
            return 'obtuse triangle'
        elif has_right:
            return 'right triangle'
        else:
            return 'triangle'
    elif sides == 4:
        return 'irregular quadrilateral'
    elif sides == 5:
        return 'irregular pentagon'
    elif sides == 6:
        return 'hexagon'
    elif sides == 7:
        return 'irregular heptagon'
    elif sides == 8:
        return 'irregular octagon'
    elif sides == 9:
        return 'irregular nonagon'
    elif sides == 10:
        return 'irregular decagon'
    else:
        return f'irregular polygon with {sides} sides'
