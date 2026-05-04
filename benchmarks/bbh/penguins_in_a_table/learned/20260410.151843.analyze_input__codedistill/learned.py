"""Auto-generated code-distilled implementation for analyze_input."""

import re

def analyze_input(text):
    # Split off options
    parts = text.split('\nOptions:\n')
    if len(parts) != 2:
        return None
    
    before_options = parts[0]
    options_text = parts[1]
    
    # Parse options
    options = []
    for m in re.finditer(r'\(([A-Z])\)\s*(.+)', options_text):
        options.append([m.group(1), m.group(2).strip()])
    
    # Find the question - last sentence/question before Options
    # Split before_options by \n to find the question line
    lines = before_options.split('\n')
    question = lines[-1].strip()
    
    # If question is empty, look further back
    remaining = '\n'.join(lines[:-1]) if len(lines) > 1 else ''
    
    # If no newlines exist before question, extract question from the blob
    if not remaining and '  ' in question:
        # The question is embedded in space-separated text
        # Find the last sentence that contains '?'
        q_match = re.search(r'(?:For example:.*?cm\.\s+)(.*\?)\s*$', question)
        if q_match:
            question = q_match.group(1).strip()
        else:
            # Try to find question after last period+spaces
            q_match = re.search(r'\.\s{2,}([^.]*\?)\s*$', question)
            if q_match:
                question = q_match.group(1).strip()
    
    # Now parse the penguin table from the initial blob
    # The initial text always starts with "Here is a table..."
    # Find the embedded table in the preamble
    blob_match = re.search(
        r'Here is a table where the first line is a header and each subsequent line is a penguin:\s+'
        r'(name,\s*age,\s*height \(cm\),\s*weight \(kg\))\s+'
        r'((?:[A-Z][a-z]+,\s*\d+,\s*\d+,\s*\d+\s*)+)',
        before_options
    )
    
    penguin_header = []
    penguin_rows = []
    
    if blob_match:
        header_str = blob_match.group(1)
        penguin_header = [h.strip() for h in header_str.split(',')]
        rows_str = blob_match.group(2).strip()
        # Split rows by pattern
        row_matches = re.findall(r'([A-Z][a-z]+),\s*(\d+),\s*(\d+),\s*(\d+)', rows_str)
        for rm in row_matches:
            penguin_rows.append(list(rm))
    
    # Check for "add a penguin" with newline data
    add_match = re.search(r'We now add a penguin to the table:\n([A-Z][a-z]+,\s*\d+,\s*\d+,\s*\d+)', before_options)
    added_name = None
    added_row = None
    if add_match:
        add_data = add_match.group(1)
        parts_add = [x.strip() for x in add_data.split(',')]
        added_name = parts_add[0]
        added_row = parts_add
    
    # Check for delete
    delete_match = re.search(r'We then delete the penguin named (\w+) from the table', before_options)
    deleted_name = None
    if delete_match:
        deleted_name = delete_match.group(1)
    
    # Check for giraffe table
    giraffe_match = re.search(
        r'And here is a similar table, but listing giraffes:\n'
        r'(name,\s*age,\s*height \(cm\),\s*weight \(kg\))\n'
        r'((?:[A-Z][a-z]+,\s*\d+,\s*\d+,\s*\d+\n?)+)',
        before_options
    )
    
    giraffe_header = []
    giraffe_rows = []
    if giraffe_match:
        giraffe_header = [h.strip() for h in giraffe_match.group(1).split(',')]
        giraffe_lines = giraffe_match.group(2).strip().split('\n')
        for gl in giraffe_lines:
            giraffe_rows.append([x.strip() for x in gl.split(',')])
    
    # Determine which table to return based on question context
    has_giraffes = bool(giraffe_match)
    
    # Check what the question asks about
    q_lower = question.lower()
    asks_about_giraffe_only = False
    asks_about_penguin_only = False
    asks_about_all = False
    
    if 'giraffe' in q_lower and 'penguin' not in q_lower and 'animal' not in q_lower and 'species' not in q_lower:
        asks_about_giraffe_only = True
    elif 'penguin' in q_lower and 'giraffe' not in q_lower and 'animal' not in q_lower and 'species' not in q_lower:
        asks_about_penguin_only = True
    elif 'animal' in q_lower or 'species' in q_lower:
        asks_about_all = True
    elif 'alphabetic order' in q_lower and has_giraffes and 'giraffe' not in q_lower and 'penguin' not in q_lower:
        asks_about_all = True
    
    # Build the table
    table = []
    operations = []
    
    if has_giraffes and asks_about_giraffe_only:
        # Only giraffe table
        table.append(giraffe_header)
        table.extend(giraffe_rows)
    elif has_giraffes and (asks_about_all or ('alphabetic order' in q_lower and 'penguin' not in q_lower and 'giraffe' not in q_lower)):
        # Merged tables
        if asks_about_all and 'penguin' in q_lower and 'giraffe' in q_lower:
            # Both mentioned
            table.append(penguin_header)
            for r in penguin_rows:
                table.append(r)
            if added_row:
                table.append(added_row)
            table.extend(giraffe_rows)
        else:
            table.append(penguin_header)
            for r in penguin_rows:
                table.append(r)
            if added_row:
                table.append(added_row)
            table.extend(giraffe_rows)
    elif has_giraffes and asks_about_penguin_only:
        # Penguin table with additions
        table.append(penguin_header)
        for r in penguin_rows:
            table.append(r)
        if added_row:
            table.append(added_row)
    else:
        # No giraffes or default
        table.append(penguin_header)
        for r in penguin_rows:
            table.append(r)
        if added_row:
            table.append(added_row)
        # Handle delete for table
        if deleted_name:
            table = [table[0]] + [r for r in table[1:] if r[0] != deleted_name]
    
    # Build operations list
    if added_row and deleted_name:
        if not has_giraffes:
            operations = [f'{added_name} added', f'{deleted_name} deleted']
    elif deleted_name and not added_row:
        operations = [f'Delete the penguin named {deleted_name}']
    elif added_row and not deleted_name and not has_giraffes:
        operations = []
    
    return [table, operations, question, options]
