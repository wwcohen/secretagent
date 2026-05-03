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
    
    # Clean up coordinate formatting (remove trailing zeros after decimal, but keep at least one decimal if there's a dot)
    def format_coord(val):
        f = float(val)
        # If it's an integer value, return without decimal
        if f == int(f) and '.' not in val:
            return str(int(f))
        # Otherwise return the float representation
        result = str(f)
        return result
    
    x_fmt = format_coord(x)
    y_fmt = format_coord(y)
    
    if cmd_type == 'M':
        return f'Move to ({x_fmt}, {y_fmt})'
    elif cmd_type == 'L':
        if previous_command is None:
            return None
        
        # Parse the previous command to get the "from" coordinates
        prev_match = re.match(r'([ML])\s+([\d.]+),([\d.]+)', previous_command.strip())
        if not prev_match:
            return None
        
        prev_x = format_coord(prev_match.group(2))
        prev_y = format_coord(prev_match.group(3))
        
        return f'Draw a line from ({prev_x}, {prev_y}) to ({x_fmt}, {y_fmt})'
    
    return None
