"""Auto-generated code-distilled implementation for compute_angle."""

import math
import re

def compute_angle(cmd1, cmd2, cmd3):
    def parse_point(cmd):
        # Extract coordinates from SVG command
        # Handle M, L, A and other commands
        nums = re.findall(r'[-+]?\d*\.?\d+', cmd)
        if not nums or len(nums) < 2:
            return None
        # For A commands, the last two numbers are the endpoint
        # For M/L commands, the numbers are x,y
        cmd_letter = cmd.strip()[0].upper()
        if cmd_letter == 'A':
            # A rx,ry x-rotation large-arc-flag sweep-flag x,y
            # last two numbers are the point
            return (float(nums[-2]), float(nums[-1]))
        else:
            return (float(nums[0]), float(nums[1]))
    
    A = parse_point(cmd1)
    B = parse_point(cmd2)
    C = parse_point(cmd3)
    
    if A is None or B is None or C is None:
        return None
    
    # Vectors: AB (incoming direction) and BC (outgoing direction)
    AB = (B[0] - A[0], B[1] - A[1])
    BC = (C[0] - B[0], C[1] - B[1])
    
    mag_AB = math.sqrt(AB[0]**2 + AB[1]**2)
    mag_BC = math.sqrt(BC[0]**2 + BC[1]**2)
    
    if mag_AB < 1e-10 or mag_BC < 1e-10:
        return None
    
    dot = AB[0]*BC[0] + AB[1]*BC[1]
    cos_angle = max(-1.0, min(1.0, dot / (mag_AB * mag_BC)))
    angle_rad = math.acos(cos_angle)
    angle_deg = math.degrees(angle_rad)
    
    rounded = round(angle_deg)
    
    if abs(rounded - 180) <= 2:
        return 'straight angle'
    elif abs(rounded - 90) <= 2:
        return 'right angle'
    elif abs(rounded - 90) <= 5:
        return f'approximately {rounded} degrees'
    elif rounded < 30:
        return f'Slight right turn (approximately {rounded} degrees)'
    elif rounded < 90:
        if rounded >= 75:
            return f'acute angle (approximately {rounded} degrees)'
        elif rounded >= 40 and rounded <= 65:
            return f'Acute angle of approximately {rounded} degrees'
        else:
            return 'acute angle'
    elif rounded > 90 and rounded <= 140:
        if rounded >= 125:
            return f'obtuse angle of approximately {rounded} degrees'
        elif rounded >= 110:
            return f'Obtuse angle (approximately {rounded} degrees)'
        else:
            return 'obtuse angle'
    else:
        return 'obtuse angle'
