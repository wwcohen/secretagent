"""Auto-generated code-distilled implementation for table_operation."""

import re
import copy

def table_operation(table, instruction):
    table = copy.deepcopy(table)
    header = table[0]
    rows = table[1:]
    
    # Check for delete operation
    delete_match = re.search(r'delete.*named\s+(\w+)', instruction, re.IGNORECASE)
    if delete_match:
        name = delete_match.group(1)
        new_rows = [row for row in rows if row[0] != name]
        return [header] + new_rows
    
    # Check for add operation
    add_match = re.search(r'add.*?(?:penguin|table)[:\s]+(\w+),\s*(\w+),\s*(\w+),\s*(\w+)', instruction, re.IGNORECASE)
    if add_match:
        new_row = [add_match.group(1), add_match.group(2), add_match.group(3), add_match.group(4)]
        rows.append(new_row)
        return [header] + rows
    
    # Check for sort operation
    if re.search(r'sort.*(?:alphabetic|alphabetical)', instruction, re.IGNORECASE):
        rows.sort(key=lambda row: row[0])
        return [header] + rows
    
    # Check for convert operation
    convert_match = re.search(r'convert\s+(\w+)\s+from\s+(\w+)\s+to\s+(\w+)', instruction, re.IGNORECASE)
    if convert_match:
        column_name = convert_match.group(1)
        from_unit = convert_match.group(2)
        to_unit = convert_match.group(3)
        
        # Find the column index
        col_idx = None
        for i, h in enumerate(header):
            if column_name.lower() in h.lower() and from_unit.lower() in h.lower():
                col_idx = i
                break
        
        if col_idx is not None:
            # Determine conversion factor
            conversion_factors = {
                ('cm', 'm'): 0.01,
                ('m', 'cm'): 100,
                ('kg', 'g'): 1000,
                ('g', 'kg'): 0.001,
                ('km', 'm'): 1000,
                ('m', 'km'): 0.001,
            }
            
            factor = conversion_factors.get((from_unit.lower(), to_unit.lower()), None)
            
            if factor is not None:
                # Update header
                new_header = header[:]
                new_header[col_idx] = header[col_idx].replace(from_unit, to_unit)
                
                # Update values
                new_rows = []
                for row in rows:
                    new_row = row[:]
                    try:
                        val = float(new_row[col_idx]) * factor
                        # Format: remove trailing zeros
                        if val == int(val):
                            new_row[col_idx] = str(int(val))
                        else:
                            new_row[col_idx] = str(val).rstrip('0').rstrip('.')
                    except ValueError:
                        pass
                    new_rows.append(new_row)
                
                return [new_header] + new_rows
        
        return table
    
    # Default: verification statements or descriptions - return table unchanged
    return table
