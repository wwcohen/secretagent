"""Auto-generated code-distilled implementation for describe_command."""

def describe_command(command, previous_command=None):
    import re
    
    def parse_command(cmd):
        """Parse a command string and return (type, x_str, y_str)"""
        match = re.match(r'([A-Za-z])\s+([-\d.]+),([-\d.]+)', cmd.strip())
        if match:
            return match.group(1), match.group(2), match.group(3)
        return None
    
    def format_num(s):
        """Format a number string: preserve decimal point and digits, but normalize."""
        # Parse as float and check if it has a decimal in the original
        if '.' in s:
            # Preserve the representation but normalize
            # Split into integer and decimal parts
            parts = s.split('.')
            int_part = parts[0]
            dec_part = parts[1] if len(parts) > 1 else ''
            # Remove leading zeros from int part (but keep at least one digit)
            int_val = str(int(int_part)) if int_part else '0'
            # Keep decimal part as-is (preserve trailing zeros only if they were there)
            return f"{int_val}.{dec_part}"
        else:
            # No decimal point - but we need to check expected output
            # From examples, integers like "41" from "41.0" should stay "41.0"
            # But the input already has "41.0" so this branch is for pure integers
            return str(int(s))
    
    parsed = parse_command(command)
    if parsed is None:
        return None
    
    cmd_type, x_str, y_str = parsed
    x_fmt = format_num(x_str)
    y_fmt = format_num(y_str)
    
    if cmd_type == 'M':
        return f'Move to ({x_fmt}, {y_fmt})'
    elif cmd_type == 'L':
        if previous_command is None:
            return None
        prev_parsed = parse_command(previous_command)
        if prev_parsed is None:
            return None
        _, px_str, py_str = prev_parsed
        px_fmt = format_num(px_str)
        py_fmt = format_num(py_str)
        return f'Draw a line from ({px_fmt}, {py_fmt}) to ({x_fmt}, {y_fmt})'
    else:
        return None
