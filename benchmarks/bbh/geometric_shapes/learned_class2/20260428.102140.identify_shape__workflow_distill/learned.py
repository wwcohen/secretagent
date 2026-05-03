"""Auto-generated workflow-distilled implementation for identify_shape.

Calls existing tools from ptools.
"""

from ptools import *

import re
import math
from typing import List, Tuple, Optional


def identify_shape(input: str) -> str:
    """Identify the geometric shape drawn by an SVG path element.
    
    Workflow:
    1. Extract the SVG path data and multiple-choice options
    2. Parse the path to determine the number of vertices and types of commands
    3. Analyze geometric properties to identify the shape
    4. Match against the available options
    """
    # Extract path data
    path_match = re.search(r'd="([^"]+)"', input)
    if not path_match:
        return None
    path_data = path_match.group(1)
    
    # Extract options
    options = {}
    option_matches = re.findall(r'\(([A-Z])\)\s+(\w+)', input)
    for letter, shape_name in option_matches:
        options[letter] = shape_name.lower()
    
    # Reverse mapping: shape name -> letter
    name_to_letter = {}
    for letter, name in options.items():
        name_to_letter[name] = letter
    
    # Parse SVG path commands
    has_arc = 'A' in path_data or 'a' in path_data
    
    if has_arc:
        # Check if it's a full ellipse/circle or a sector
        # Count arc commands
        arc_commands = re.findall(r'[Aa]\s+[\d.,\s-]+', path_data)
        line_commands = re.findall(r'[Ll]\s+[\d.,\s-]+', path_data)
        
        # Count the number of arc segments
        num_arcs = len(re.findall(r'[Aa]\s', path_data))
        num_lines = len(re.findall(r'[Ll]\s', path_data))
        
        if num_arcs >= 2 and num_lines == 0:
            # Two arcs forming a complete shape - likely circle or ellipse
            # Check if it's a circle or ellipse by examining radii
            arc_params = re.findall(r'[Aa]\s+([\d.]+),([\d.]+)', path_data)
            if arc_params:
                rx, ry = float(arc_params[0][0]), float(arc_params[0][1])
                if abs(rx - ry) < 0.01:
                    # Circle
                    if 'circle' in name_to_letter:
                        return f'({name_to_letter["circle"]})'
                    elif 'ellipse' in name_to_letter:
                        return f'({name_to_letter["ellipse"]})'
                else:
                    # Ellipse
                    if 'ellipse' in name_to_letter:
                        return f'({name_to_letter["ellipse"]})'
                    elif 'circle' in name_to_letter:
                        return f'({name_to_letter["circle"]})'
            # Default for two arcs
            if 'ellipse' in name_to_letter:
                return f'({name_to_letter["ellipse"]})'
            elif 'circle' in name_to_letter:
                return f'({name_to_letter["circle"]})'
        elif num_arcs == 1 and num_lines >= 1:
            # Arc + lines = sector
            if 'sector' in name_to_letter:
                return f'({name_to_letter["sector"]})'
        elif num_arcs >= 1:
            # Could still be sector or circle variant
            if num_lines > 0 and 'sector' in name_to_letter:
                return f'({name_to_letter["sector"]})'
            if 'circle' in name_to_letter:
                return f'({name_to_letter["circle"]})'
            if 'ellipse' in name_to_letter:
                return f'({name_to_letter["ellipse"]})'
    
    # For line-based shapes, count unique vertices
    # Extract all coordinate points from M and L commands
    points = []
    # Parse all coordinates after M and L commands
    # Tokenize the path data
    tokens = re.split(r'([MLZHVCSQTAmlzhvcsqta])', path_data)
    
    current_cmd = None
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if re.match(r'^[MLZHVCSQTAmlzhvcsqta]$', token):
            current_cmd = token
            continue
        if current_cmd in ('M', 'L'):
            # Extract coordinate pairs
            coords = re.findall(r'([-\d.]+)\s*,\s*([-\d.]+)', token)
            for x, y in coords:
                points.append((float(x), float(y)))
    
    if not points:
        return None
    
    # Remove duplicate consecutive points and find unique vertices
    unique_points = []
    for p in points:
        is_dup = False
        for up in unique_points:
            if abs(p[0] - up[0]) < 0.01 and abs(p[1] - up[1]) < 0.01:
                is_dup = True
                break
        if not is_dup:
            unique_points.append(p)
    
    # Check if the last point is the same as the first (closed path)
    if len(unique_points) >= 2:
        first = unique_points[0]
        last = unique_points[-1]
        if abs(first[0] - last[0]) < 0.01 and abs(first[1] - last[1]) < 0.01:
            unique_points = unique_points[:-1]
    
    num_vertices = len(unique_points)
    
    # Map vertex count to shape name
    vertex_to_shape = {
        2: 'line',
        3: 'triangle',
        4: None,  # Could be rectangle, kite, trapezoid, etc.
        5: 'pentagon',
        6: 'hexagon',
        7: 'heptagon',
        8: 'octagon',
    }
    
    if num_vertices == 2:
        if 'line' in name_to_letter:
            return f'({name_to_letter["line"]})'
    
    elif num_vertices == 3:
        if 'triangle' in name_to_letter:
            return f'({name_to_letter["triangle"]})'
    
    elif num_vertices == 4:
        # Determine which 4-sided shape it is
        # Check available options to narrow down
        four_sided_options = []
        for name in ['rectangle', 'kite', 'trapezoid']:
            if name in name_to_letter:
                four_sided_options.append(name)
        
        if len(four_sided_options) == 1:
            return f'({name_to_letter[four_sided_options[0]]})'
        
        if len(four_sided_options) == 0:
            # Maybe it's listed differently
            return None
        
        # Need to distinguish between rectangle, kite, trapezoid
        p = unique_points
        
        def dist(a, b):
            return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)
        
        # Side lengths
        sides = []
        for i in range(4):
            sides.append(dist(p[i], p[(i+1) % 4]))
        
        # Diagonal lengths
        d1 = dist(p[0], p[2])
        d2 = dist(p[1], p[3])
        
        # Check for rectangle: opposite sides equal and diagonals equal
        opp_sides_equal = (abs(sides[0] - sides[2]) < 0.5 and abs(sides[1] - sides[3]) < 0.5)
        diag_equal = abs(d1 - d2) < 0.5
        
        if 'rectangle' in name_to_letter and opp_sides_equal and diag_equal:
            return f'({name_to_letter["rectangle"]})'
        
        # Check for kite: two pairs of consecutive equal sides
        is_kite = False
        if (abs(sides[0] - sides[1]) < 0.5 and abs(sides[2] - sides[3]) < 0.5):
            is_kite = True
        if (abs(sides[1] - sides[2]) < 0.5 and abs(sides[3] - sides[0]) < 0.5):
            is_kite = True
        
        if 'kite' in name_to_letter and is_kite:
            return f'({name_to_letter["kite"]})'
        
        # Check for trapezoid: one pair of parallel sides
        def slope(a, b):
            if abs(b[0] - a[0]) < 0.001:
                return float('inf')
            return (b[1] - a[1]) / (b[0] - a[0])
        
        slopes = []
        for i in range(4):
            slopes.append(slope(p[i], p[(i+1) % 4]))
        
        is_trapezoid = False
        # Check if opposite sides are parallel
        for i in range(2):
            s1 = slopes[i]
            s2 = slopes[i+2]
            if s1 == float('inf') and s2 == float('inf'):
                is_trapezoid = True
            elif s1 != float('inf') and s2 != float('inf') and abs(s1 - s2) < 0.1:
                is_trapezoid = True
        
        if 'trapezoid' in name_to_letter and is_trapezoid:
            return f'({name_to_letter["trapezoid"]})'
        
        # If rectangle check with looser tolerance
        if 'rectangle' in name_to_letter and opp_sides_equal:
            return f'({name_to_letter["rectangle"]})'
        
        if 'kite' in name_to_letter and is_kite:
            return f'({name_to_letter["kite"]})'
        
        if 'trapezoid' in name_to_letter:
            return f'({name_to_letter["trapezoid"]})'
        
        if 'rectangle' in name_to_letter:
            return f'({name_to_letter["rectangle"]})'
        if 'kite' in name_to_letter:
            return f'({name_to_letter["kite"]})'
    
    elif num_vertices == 5:
        if 'pentagon' in name_to_letter:
            return f'({name_to_letter["pentagon"]})'
    
    elif num_vertices == 6:
        if 'hexagon' in name_to_letter:
            return f'({name_to_letter["hexagon"]})'
    
    elif num_vertices == 7:
        if 'heptagon' in name_to_letter:
            return f'({name_to_letter["heptagon"]})'
    
    elif num_vertices == 8:
        if 'octagon' in name_to_letter:
            return f'({name_to_letter["octagon"]})'
    
    # Fallback: use LLM-based tool
    try:
        result = describe_shape(input)
        if result:
            result_lower = result.lower().strip()
            # Try to match result to an option
            for name, letter in name_to_letter.items():
                if name in result_lower:
                    return f'({letter})'
            # Try extract_option_letter
            letter = extract_option_letter(result)
            if letter:
                return letter
    except:
        pass
    
    return None
