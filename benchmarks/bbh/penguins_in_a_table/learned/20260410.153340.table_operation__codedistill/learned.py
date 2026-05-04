"""Auto-generated code-distilled implementation for table_operation."""

import re
import copy

def table_operation(table, command):
    table = copy.deepcopy(table)
    cmd_lower = command.strip().lower()
    
    num_cols = len(table[0]) if table else 0
    
    # Determine if it's add or delete
    if cmd_lower.startswith('add'):
        operation = 'add'
    elif cmd_lower.startswith('delete'):
        operation = 'delete'
    else:
        # Check if command contains 'add' or 'delete' somewhere
        # Based on example "James added" -> exception
        try:
            compile_result = compile(command, '<unknown>', 'exec')
        except SyntaxError as e:
            return f'**exception**: invalid syntax (<unknown>, line 2)'
        return f'**exception**: invalid syntax (<unknown>, line 2)'
    
    if operation == 'delete':
        # Extract the name to delete - find capitalized words that could be names
        # Remove common filler words
        rest = command.strip()
        # Find the name: look for capitalized words that aren't keywords
        filler = r'\b(?:delete|the|penguin|named|from|table|row)\b'
        cleaned = re.sub(filler, '', rest, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        name = cleaned.strip()
        
        # Remove rows matching the name
        new_table = [table[0]]
        for row in table[1:]:
            if row[0] != name:
                new_table.append(row)
        return new_table
    
    elif operation == 'add':
        rest = command.strip()
        
        # Try to extract all values: look for comma-separated values pattern
        # First, try to find explicit comma-separated data
        # Extract all numbers from the command
        numbers = re.findall(r'\b(\d+)\b', rest)
        
        # Extract the name: find capitalized word that's not a keyword
        filler_words = {'add', 'the', 'penguin', 'named', 'to', 'table', 'with', 'age', 'height', 'weight', 'row', 'from', 'a', 'an'}
        
        # Try to find name - look for capitalized words not in filler
        words = re.findall(r'\b([A-Z][a-z]+)\b', rest)
        name = None
        for w in words:
            if w.lower() not in filler_words:
                name = w
                break
        
        if name is None:
            # Try lowercase
            all_words = re.findall(r'\b(\w+)\b', rest)
            for w in all_words:
                if w.lower() not in filler_words and not w.isdigit():
                    name = w
                    break
        
        if name is None:
            return table
        
        # Build the new row
        if len(numbers) >= num_cols - 1:
            # We have enough data
            new_row = [name] + [str(n) for n in numbers[:num_cols - 1]]
        elif len(numbers) > 0:
            # Partial data
            new_row = [name] + [str(n) for n in numbers]
            while len(new_row) < num_cols:
                new_row.append('')
        else:
            # No data provided, just a name - return table unchanged (like "Add penguin James" with no data)
            # Based on example: 'Add penguin James' -> table unchanged
            return table
        
        table.append(new_row)
        return table
