"""Auto-generated code-distilled implementation for compute_angle."""

import math
import re

def compute_angle(cmd1, cmd2, cmd3):
    def parse_point(cmd):
        match = re.match(r'[ML]\s*([-\d.]+),([-\d.]+)', cmd.strip())
        if not match:
            return None
        return (float(match.group(1)), float(match.group(2)))
    
    A = parse_point(cmd1)
    B = parse_point(cmd2)
    C = parse_point(cmd3)
    
    if A is None or B is None or C is None:
        return None
    
    # Vectors BA and BC
    ba = (A[0] - B[0], A[1] - B[1])
    bc = (C[0] - B[0], C[1] - B[1])
    
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.sqrt(ba[0]**2 + ba[1]**2)
    mag_bc = math.sqrt(bc[0]**2 + bc[1]**2)
    
    if mag_ba == 0 or mag_bc == 0:
        return None
    
    cos_angle = dot / (mag_ba * mag_bc)
    cos_angle = max(-1, min(1, cos_angle))
    
    angle_deg = math.degrees(math.acos(cos_angle))
    
    # Round to nearest integer
    rounded = round(angle_deg)
    
    # Check if it's exactly a multiple of 10 (or very close)
    nearest_10 = round(angle_deg / 10) * 10
    
    if abs(angle_deg - 180) < 1:
        return 'The angle is 180 degrees.'
    elif abs(angle_deg - 90) < 1:
        return 'The angle is 90 degrees.'
    elif abs(angle_deg - nearest_10) < 3 and nearest_10 not in (90,):
        if nearest_10 == round(angle_deg):
            return f'The angle is {int(nearest_10)} degrees.'
        else:
            return f'The angle is approximately {int(nearest_10)} degrees.'
    elif angle_deg < 90:
        return 'acute angle'
    elif angle_deg > 90:
        return 'obtuse angle'
    else:
        return None
