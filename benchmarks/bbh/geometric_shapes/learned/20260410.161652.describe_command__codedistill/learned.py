"""Auto-generated code-distilled implementation for describe_command."""

def describe_command(command, previous_command=None):
    """Describe an SVG path command in natural language."""
    import re
    
    # Parse the current command
    match = re.match(r'^([ML])\s+([\d.]+),([\d.]+)$', command.strip())
    if not match:
        return None
    
    cmd_type = match.group(1)
    x = match.group(2)
    y = match.group(3)
    
    # Format coordinates: remove trailing zeros but keep at least one decimal place
    def format_coord(s):
        # Parse as float and format
        val = float(s)
        # Check if it's an integer value
        if val == int(val):
            return f"{val:.1f}"
        else:
            # Remove trailing zeros after decimal point, but keep at least one decimal
            formatted = f"{val:g}"
            if '.' not in formatted:
                formatted += '.0'
            return formatted
    
    fx = format_coord(x)
    fy = format_coord(y)
    
    if cmd_type == 'M':
        return f'Move to ({fx}, {fy})'
    elif cmd_type == 'L':
        if previous_command is None:
            return None
        
        # Parse previous command to get the starting point
        prev_match = re.match(r'^([ML])\s+([\d.]+),([\d.]+)$', previous_command.strip())
        if not prev_match:
            return None
        
        prev_x = format_coord(prev_match.group(2))
        prev_y = format_coord(prev_match.group(3))
        
        return f'Draw a line from ({prev_x}, {prev_y}) to ({fx}, {fy})'
    
    return None
