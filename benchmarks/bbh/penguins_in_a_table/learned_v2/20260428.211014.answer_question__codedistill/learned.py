"""Auto-generated code-distilled implementation for answer_question."""

import re
import math

def answer_question(table, question):
    headers = table[0]
    rows = table[1:]
    
    # Filter out any repeated header rows and collect "species" groups
    data_rows = []
    header_count = 0
    for row in rows:
        if row == headers:
            header_count += 1
        else:
            data_rows.append(row)
    
    num_species = header_count + 1  # initial header + repeated headers
    
    q = question.lower()
    
    # How many species
    if 'how many species' in q:
        return str(num_species)
    
    # How many columns
    if 'how many columns' in q:
        return str(len(headers))
    
    # How many animals/rows
    if re.search(r'how many (animals|penguins|giraffes|entries|rows)', q):
        # Check for compound conditions
        compound = re.search(r'how many \w+ are (.+)\?', q)
        if compound:
            condition_str = compound.group(1)
            count = _count_with_conditions(headers, data_rows, condition_str)
            return str(count)
        return str(len(data_rows))
    
    # Average
    if 'average' in q:
        col_idx = _find_column_in_question(headers, q)
        if col_idx is not None:
            vals = [float(row[col_idx]) for row in data_rows]
            # Use simple division
            avg = sum(vals) / len(vals)
            # Format: remove trailing zeros but keep one decimal if needed
            if avg == int(avg):
                return str(float(avg))
            return str(avg)
    
    # Cumulated / sum / total
    if any(w in q for w in ['cumulated', 'total', 'sum of']):
        col_idx = _find_column_in_question(headers, q)
        if col_idx is not None:
            vals = [float(row[col_idx]) for row in data_rows]
            s = sum(vals)
            return str(int(s)) if s == int(s) else str(s)
    
    # First/last sorted by alphabetic order
    if 'alphabetic order' in q:
        names = [row[0] for row in data_rows]
        names_sorted = sorted(names)
        if 'first' in q:
            return names_sorted[0]
        elif 'last' in q:
            return names_sorted[-1]
    
    # Superlative: heaviest, oldest, youngest, tallest, lightest, shortest, etc.
    superlative_map = {
        'heaviest': ('weight', True),
        'lightest': ('weight', False),
        'oldest': ('age', True),
        'youngest': ('age', False),
        'tallest': ('height', True),
        'taller': ('height', True),
        'shortest': ('height', False),
        'shorter': ('height', False),
    }
    
    for word, (col_key, find_max) in superlative_map.items():
        if word in q:
            col_idx = _find_column_by_keyword(headers, col_key)
            if col_idx is not None:
                if find_max:
                    best_row = max(data_rows, key=lambda r: float(r[col_idx]))
                else:
                    best_row = min(data_rows, key=lambda r: float(r[col_idx]))
                return best_row[0]
    
    # "younger than X" / "older than X"
    comp_match = re.search(r'(younger|older|heavier|lighter|taller|shorter) than (\w+)', q)
    if comp_match:
        comp_word = comp_match.group(1)
        ref_name = comp_match.group(2)
        col_key_map = {
            'younger': 'age', 'older': 'age',
            'heavier': 'weight', 'lighter': 'weight',
            'taller': 'height', 'shorter': 'height',
        }
        less_than_set = {'younger', 'lighter', 'shorter'}
        col_key = col_key_map[comp_word]
        col_idx = _find_column_by_keyword(headers, col_key)
        if col_idx is not None:
            ref_val = None
            for row in data_rows:
                if row[0].lower() == ref_name.lower():
                    ref_val = float(row[col_idx])
                    break
            if ref_val is not None:
                is_less = comp_word in less_than_set
                results = []
                for row in data_rows:
                    val = float(row[col_idx])
                    if row[0].lower() != ref_name.lower():
                        if is_less and val < ref_val:
                            results.append(row[0])
                        elif not is_less and val > ref_val:
                            results.append(row[0])
                if len(results) == 1:
                    return results[0]
                elif results:
                    return ', '.join(results)
    
    # "less than N years old" / comparison with number
    less_match = re.search(r'(?:which \w+ is )?less than (\d+\.?\d*) (?:years old|kg|cm|m)', q)
    if less_match and 'how many' not in q:
        val_threshold = float(less_match.group(1))
        col_idx = _find_column_in_question(headers, q)
        if col_idx is not None:
            results = [row[0] for row in data_rows if float(row[col_idx]) < val_threshold]
            if len(results) == 1:
                return results[0]
            elif results:
                return ', '.join(results)
    
    # Lookup: "name of the X m tall penguin" or "name of the X kg penguin"
    lookup_match = re.search(r'(?:name of the )(\d+\.?\d*)\s*(m|cm|kg|years?)', q)
    if lookup_match:
        val = lookup_match.group(1)
        unit = lookup_match.group(2)
        col_idx = _find_column_by_unit(headers, unit)
        if col_idx is not None:
            for row in data_rows:
                if row[col_idx] == val:
                    return row[0]
    
    return None


def _find_column_by_keyword(headers, keyword):
    for i, h in enumerate(headers):
        if keyword in h.lower():
            return i
    return None


def _find_column_by_unit(headers, unit):
    unit_map = {'m': 'height', 'cm': 'height', 'kg': 'weight', 'year': 'age', 'years': 'age'}
    keyword = unit_map.get(unit, unit)
    return _find_column_by_keyword(headers, keyword)


def _find_column_in_question(headers, q):
    # Try to match header keywords in question
    for keyword in ['age', 'height', 'weight']:
        if keyword in q:
            return _find_column_by_keyword(headers, keyword)
    if 'years old' in q or 'year old' in q:
        return _find_column_by_keyword(headers, 'age')
    return None


def _count_with_conditions(headers, data_rows, condition_str):
    # Parse conditions joined by "and"
    parts = re.split(r'\band\b', condition_str)
    matching = data_rows
    for part in parts:
        part = part.strip()
        m = re.search(r'(more|less|greater|fewer) than (\d+\.?\d*)\s*(years? old|kg|cm|m\b)?', part)
        if m:
            direction = m.group(1)
            threshold = float(m.group(2))
            unit_hint = m.group(3) if m.group(3) else ''
            
            if 'year' in unit_hint or 'year' in part or 'age' in part:
                col_idx = _find_column_by_keyword(headers, 'age')
            elif 'weight' in part or ('kg' in unit_hint and 'height' not in part):
                col_idx = _find_column_by_keyword(headers, 'weight')
            elif 'height' in part or 'cm' in unit_hint or ('m' in unit_hint and 'height' not in headers):
                col_idx = _find_column_by_keyword(headers, 'height')
            elif 'kg' in part:
                col_idx = _find_column_by_keyword(headers, 'weight')
            else:
                col_idx = None
            
            if col_idx is not None:
                if direction in ('more', 'greater'):
                    matching = [r for r in matching if float(r[col_idx]) > threshold]
                else:
                    matching = [r for r in matching if float(r[col_idx]) < threshold]
    
    # Deduplicate by name for counting
    seen = set()
    unique = []
    for r in matching:
        key = tuple(r)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    return len(unique)
