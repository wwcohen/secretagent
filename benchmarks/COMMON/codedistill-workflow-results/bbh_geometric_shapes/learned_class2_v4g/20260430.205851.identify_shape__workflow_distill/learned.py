"""Auto-generated workflow-distilled implementation for identify_shape.

Calls existing tools from ptools.
"""

from ptools import *

import re

def identify_shape(input: str) -> str:
    """
    Solves the geometric shapes task end-to-end by orchestrating the provided sub-tools.
    Returns the selected multiple-choice option letter, formatted like '(A)'.
    """
    try:
        # 1. Extract path and options
        path = None
        options = []
        try:
            parsed = extract_path_and_options(input)
            if isinstance(parsed, tuple) and len(parsed) == 2:
                path, options = parsed
        except Exception:
            pass
            
        # Pure-Python fallback for extraction if the LLM tool fails
        if not path or not options:
            path_match = re.search(r'<path\s+d="([^"]+)"', input)
            if path_match:
                path = path_match.group(1)
            
            opts_section = input.split("Options:\n")[-1] if "Options:\n" in input else input
            for line in opts_section.strip().split('\n'):
                m = re.match(r'\(([A-Z])\)\s+(.*)', line.strip())
                if m:
                    options.append((m.group(1), m.group(2)))
                    
        if not path or not options:
            return None

        # 2. Decompose path into individual commands
        commands = None
        try:
            commands = decompose_path(path)
        except Exception:
            pass
            
        # Pure-Python fallback for decomposition
        if not commands:
            cmds = re.findall(r'[MLCAZ][^MLCAZ]*', path, flags=re.IGNORECASE)
            commands = [c.strip() for c in cmds if c.strip()]
            
        if not commands:
            return None

        # 3. Normalize path (using the module's pure-Python tool)
        norm_commands = None
        try:
            norm_commands = normalize_path(commands)
        except Exception:
            pass
            
        if not norm_commands:
            norm_commands = commands

        # 4. Describe each SVG command
        descriptions = []
        for cmd in norm_commands:
            try:
                desc = describe_command(cmd)
                descriptions.append(desc)
            except Exception:
                # If command description fails, fall back to the raw command
                descriptions.append(cmd)
                
        if not descriptions:
            return None

        # 5. Describe the overall shape
        shape = None
        try:
            # First try passing the list of descriptions
            shape = describe_shape(descriptions)
        except Exception:
            try:
                # If it expects a single concatenated string
                shape = describe_shape("\n".join(descriptions))
            except Exception:
                pass
                
        if not shape:
            return None

        # 6. Select the matching option
        chosen = None
        try:
            chosen = select_option(shape, options)
        except Exception:
            pass
            
        # Pure-Python fallback for option selection
        if not chosen:
            shape_lower = str(shape).lower()
            for opt in options:
                if isinstance(opt, tuple) and len(opt) == 2:
                    if opt[1].lower() in shape_lower:
                        chosen = opt
                        break

        if not chosen:
            return None

        # 7. Extract the final option letter exactly
        if isinstance(chosen, tuple):
            letter_str = str(chosen[0])
        else:
            letter_str = str(chosen)
            
        m = re.search(r'\b([A-Z])\b', letter_str)
        if m:
            extracted_letter = m.group(1)
        else:
            m2 = re.search(r'[A-Z]', letter_str)
            if m2:
                extracted_letter = m2.group(0)
            else:
                extracted_letter = letter_str.strip().strip("()")[0].upper()
                
        return f"({extracted_letter})"

    except Exception:
        # Return None on any unexpected orchestration failure
        return None
