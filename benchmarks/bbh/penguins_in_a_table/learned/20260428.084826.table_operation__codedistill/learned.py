"""Auto-generated code-distilled implementation for table_operation."""

import re
import copy

def table_operation(table, operation):
    result = copy.deepcopy(table)
    op = operation.strip().rstrip('.')
    
    # Convert unit operation
    convert_match = re.search(r'convert\s+(\w+)\s+from\s+(\w+)\s+to\s+(\w+)', op, re.IGNORECASE)
    if convert_match:
        col_name = convert_match.group(1)
        from_unit = convert_match.group(2)
        to_unit = convert_match.group(3)
        
        header = result[0]
        col_idx = None
        for i, h in enumerate(header):
            if col_name.lower() in h.lower() and from_unit in h:
                col_idx = i
                break
        
        if col_idx is not None:
            # Update header
            result[0][col_idx] = result[0][col_idx].replace(from_unit, to_unit)
            
            # Determine conversion factor
            conversion = 1.0
            if from_unit == 'cm' and to_unit == 'm':
                conversion = 0.01
            elif from_unit == 'm' and to_unit == 'cm':
                conversion = 100
            elif from_unit == 'kg' and to_unit == 'g':
                conversion = 1000
            elif from_unit == 'g' and to_unit == 'kg':
                conversion = 0.001
            
            for row in result[1:]:
                val = float(row[col_idx]) * conversion
                # Format: remove trailing zeros
                if val == int(val):
                    row[col_idx] = str(int(val))
                else:
                    row[col_idx] = str(val).rstrip('0').rstrip('.')
        return result
    
    # Sort operation
    if re.search(r'sort', op, re.IGNORECASE) and re.search(r'alphabetic', op, re.IGNORECASE):
        header = result[0]
        rows = result[1:]
        rows.sort(key=lambda r: r[0])
        return [header] + rows
    
    # Delete operation
    delete_match = re.search(r'delete.*(?:named|penguin)\s+(\w+)', op, re.IGNORECASE)
    if delete_match:
        name = delete_match.group(1)
        header = result[0]
        rows = [r for r in result[1:] if r[0] != name]
        return [header] + rows
    
    # Add operation - look for pattern with comma-separated values
    add_match = re.search(r'add.*?:\s*(.+)', op, re.IGNORECASE)
    if not add_match:
        add_match = re.search(r'add\s+penguin\s+(.+)', op, re.IGNORECASE)
    if add_match:
        values_str = add_match.group(1).strip()
        values = [v.strip() for v in values_str.split(',')]
        if len(values) == len(result[0]):
            result.append(values)
        return result
    
    # Check if it's a delete with no match (already handled above, but just in case)
    if re.search(r'delete', op, re.IGNORECASE):
        return result
    
    # Default: no-op (informational statements, examples, etc.)
    return result
