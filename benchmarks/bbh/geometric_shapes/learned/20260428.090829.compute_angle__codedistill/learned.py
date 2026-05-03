"""Auto-generated code-distilled implementation for compute_angle."""

import math
import re

def compute_angle(cmd1, cmd2, cmd3):
    def parse_coords(cmd):
        match = re.match(r'[ML]\s*([-\d.]+),([-\d.]+)', cmd.strip())
        if not match:
            return None
        return (float(match.group(1)), float(match.group(2)))
    
    A = parse_coords(cmd1)
    B = parse_coords(cmd2)
    C = parse_coords(cmd3)
    
    if A is None or B is None or C is None:
        return None
    
    # Vectors BA and BC
    BA = (A[0] - B[0], A[1] - B[1])
    BC = (C[0] - B[0], C[1] - B[1])
    
    dot = BA[0] * BC[0] + BA[1] * BC[1]
    mag_BA = math.sqrt(BA[0]**2 + BA[1]**2)
    mag_BC = math.sqrt(BC[0]**2 + BC[1]**2)
    
    if mag_BA == 0 or mag_BC == 0:
        return None
    
    cos_angle = dot / (mag_BA * mag_BC)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    
    angle_rad = math.acos(cos_angle)
    angle_deg = math.degrees(angle_rad)
    
    # Round to nearest integer
    rounded = round(angle_deg)
    
    # Check if it's close to a "round" number (multiple of 10, or 180, 90, etc.)
    if abs(angle_deg - 180) < 2:
        return 'The angle is 180 degrees.'
    elif abs(angle_deg - 90) < 2:
        return 'right angle'
    elif abs(angle_deg - rounded) < 0.5 and rounded % 10 == 0 and rounded not in (90, 180, 0):
        return f'The angle is approximately {rounded} degrees.'
    elif angle_deg < 90:
        return 'acute angle'
    elif angle_deg > 90:
        return 'obtuse angle'
    else:
        return None
