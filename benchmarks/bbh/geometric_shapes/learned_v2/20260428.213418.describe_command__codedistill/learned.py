"""Auto-generated code-distilled implementation for describe_command."""

def describe_command(command, previous_command=None):
    import re
    
    # Parse the current command
    match = re.match(r'([ML])\s+([\d.]+),([\d.]+)', command.strip())
    if not match:
        return None
    
    cmd_type = match.group(1)
    x = match.group(2)
    y = match.group(3)
    
    # Remove trailing zeros after decimal point for clean display
    def clean_num(s):
        if '.' in s:
            # Parse and re-format to remove unnecessary trailing zeros
            val = float(s)
            # Format it back - if it's an integer, still show without trailing zeros
            result = f"{val:g}"
            return result
        return s
    
    x_clean = clean_num(x)
    y_clean = clean_num(y)
    
    if cmd_type == 'M':
        return f'Move to ({x_clean}, {y_clean})'
    elif cmd_type == 'L':
        if previous_command is None:
            return None
        
        # Parse the previous command to get the starting point
        prev_match = re.match(r'([ML])\s+([\d.]+),([\d.]+)', previous_command.strip())
        if not prev_match:
            return None
        
        prev_x = clean_num(prev_match.group(2))
        prev_y = clean_num(prev_match.group(3))
        
        return f'Draw a line from ({prev_x}, {prev_y}) to ({x_clean}, {y_clean})'
    
    return None
