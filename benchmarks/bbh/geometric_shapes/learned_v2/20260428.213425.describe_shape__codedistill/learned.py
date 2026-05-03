"""Auto-generated code-distilled implementation for describe_shape."""

import re
import math

def describe_shape(commands):
    if not commands:
        return None
    
    # Parse all points from commands
    points = []
    has_arc = False
    closes = False
    
    for cmd in commands:
        if 'Move to' in cmd:
            match = re.search(r'Move to \(([-\d.]+),\s*([-\d.]+)\)', cmd)
            if match:
                points.append((float(match.group(1)), float(match.group(2))))
        elif 'Draw a line' in cmd:
            match = re.search(r'to \(([-\d.]+),\s*([-\d.]+)\)', cmd)
            if match:
                points.append((float(match.group(1)), float(match.group(2))))
        elif 'Draw an arc' in cmd or 'arc' in cmd.lower():
            has_arc = True
            match = re.search(r'to \(([-\d.]+),\s*([-\d.]+)\)', cmd)
            if match:
                points.append((float(match.group(1)), float(match.group(2))))
        elif 'Close' in cmd or 'close' in cmd:
            closes = True
    
    if len(points) < 2:
        return None
    
    # Check if the path is closed (last point == first point, or explicit close)
    first = points[0]
    last = points[-1]
    is_closed = closes or (math.isclose(first[0], last[0], abs_tol=0.01) and math.isclose(first[1], last[1], abs_tol=0.01))
    
    if not is_closed and not has_arc:
        if len(points) == 2:
            return 'A line segment'
        return None
    
    # For closed shapes, count unique vertices
    unique_points = []
    for p in points:
        is_dup = False
        for u in unique_points:
            if math.isclose(p[0], u[0], abs_tol=0.01) and math.isclose(p[1], u[1], abs_tol=0.01):
                is_dup = True
                break
        if not is_dup:
            unique_points.append(p)
    
    n = len(unique_points)
    
    if has_arc:
        if n <= 2 and is_closed and not any('Draw a line' in cmd for cmd in commands):
            return 'A circle'
        # Sector: arc + lines back to center
        line_count = sum(1 for cmd in commands if 'Draw a line' in cmd)
        if line_count >= 2 and has_arc:
            return 'A sector'
        if has_arc and is_closed:
            return 'A sector'
        return None
    
    shape_names = {
        3: 'A triangle',
        4: None,  # Could be rectangle or kite
        5: 'A pentagon',
        6: 'A hexagon',
        7: 'A heptagon',
        8: 'An octagon',
    }
    
    if n == 4:
        # Determine if rectangle or kite
        # For now, check if it has right angles (rectangle) or two pairs of adjacent equal sides (kite)
        def dist(a, b):
            return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)
        
        sides = [dist(unique_points[i], unique_points[(i+1) % 4]) for i in range(4)]
        
        # Kite: two pairs of consecutive equal sides
        if (math.isclose(sides[0], sides[1], rel_tol=0.02) and math.isclose(sides[2], sides[3], rel_tol=0.02)) or \
           (math.isclose(sides[1], sides[2], rel_tol=0.02) and math.isclose(sides[3], sides[0], rel_tol=0.02)):
            if not math.isclose(sides[0], sides[2], rel_tol=0.02):
                return 'A kite'
        
        return 'A rectangle'
    
    return shape_names.get(n)
