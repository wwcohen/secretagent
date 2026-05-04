"""Auto-generated code-distilled implementation for answer_question."""

import re

def answer_question(table, question):
    q = question.lower()
    
    # Split tables by repeated headers
    tables = []
    current_table = []
    header = table[0]
    for row in table:
        if row == header and current_table:
            tables.append(current_table)
            current_table = [row]
        else:
            current_table.append(row)
    if current_table:
        tables.append(current_table)
    
    # How many species
    if 'how many species' in q:
        return str(len(tables))
    
    # Work with combined data rows (deduplicated) from all tables, using first header
    all_headers = tables[0][0]
    all_rows = []
    for t in tables:
        for row in t[1:]:
            all_rows.append(row)
    
    # Deduplicate rows
    seen = set()
    unique_rows = []
    for row in all_rows:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
    
    headers = all_headers
    rows = unique_rows
    
    name_col = 0 if 'name' in headers[0].lower() else None
    
    def get_col_index(keyword):
        for i, h in enumerate(headers):
            if keyword in h.lower():
                return i
        return None
    
    def get_unit(col_idx):
        h = headers[col_idx]
        m = re.search(r'\(([^)]+)\)', h)
        return m.group(1) if m else ''
    
    def numeric(val):
        try:
            return float(val)
        except:
            return None
    
    # How many columns
    if 'how many columns' in q:
        return str(len(headers))
    
    # How many animals/penguins are listed (no filter condition beyond simple)
    if re.search(r'how many (animals|penguins|giraffes) are listed', q):
        return str(len(rows))
    
    # Cannot determine gender
    if 'female' in q or 'male' in q or 'gender' in q:
        if 'gender' not in [h.lower() for h in headers] and 'sex' not in [h.lower() for h in headers]:
            return 'Cannot determine gender from the given table.'
    
    # How many with conditions
    m = re.search(r'how many \w+ are (.*)\?', q)
    if m:
        conditions_str = m.group(1)
        # Parse conditions
        parts = re.split(r'\s+and\s+', conditions_str)
        matching = rows[:]
        for part in parts:
            cm = re.search(r'(more|less|greater|fewer) than (\d+\.?\d*)\s*(years? old|year|kg|cm|m|pounds?)?', part)
            if cm:
                comp = cm.group(1)
                val = float(cm.group(2))
                unit_hint = cm.group(3) or ''
                if 'year' in unit_hint or 'old' in unit_hint:
                    col = get_col_index('age')
                elif 'kg' in unit_hint or 'weight' in part:
                    col = get_col_index('weight')
                elif 'cm' in unit_hint or 'height' in part:
                    col = get_col_index('height')
                elif 'm' in unit_hint:
                    col = get_col_index('height')
                else:
                    col = get_col_index('age')
                if col is None:
                    return None
                if comp in ('more', 'greater'):
                    matching = [r for r in matching if numeric(r[col]) is not None and numeric(r[col]) > val]
                else:
                    matching = [r for r in matching if numeric(r[col]) is not None and numeric(r[col]) < val]
            # weight more/less than X kg
            cm2 = re.search(r'weigh[t]?\s+(more|less) than (\d+\.?\d*)\s*(\w*)', part)
            if cm2 and not cm:
                comp = cm2.group(1)
                val = float(cm2.group(2))
                col = get_col_index('weight')
                if col is None:
                    return None
                if comp == 'more':
                    matching = [r for r in matching if numeric(r[col]) is not None and numeric(r[col]) > val]
                else:
                    matching = [r for r in matching if numeric(r[col]) is not None and numeric(r[col]) < val]
        return str(len(matching))
    
    # Cumulated/total age/weight/height
    m = re.search(r'cumulated (\w+)', q)
    if m:
        attr = m.group(1)
        col = get_col_index(attr)
        if col is not None:
            total = sum(numeric(r[col]) for r in rows if numeric(r[col]) is not None)
            return str(int(total)) if total == int(total) else str(total)
    
    # Average
    m = re.search(r'average (\w+)', q)
    if m:
        attr = m.group(1)
        col = get_col_index(attr)
        if col is not None:
            vals = [numeric(r[col]) for r in rows if numeric(r[col]) is not None]
            avg = sum(vals) / len(vals) if vals else 0
            # Check if it's a round number
            if avg == int(avg):
                return str(int(avg))
            # Format to match expected
            return str(round(avg, 1)) if round(avg, 1) == round(avg, 10) else str(avg)
    
    # Sorted by alphabetic order (first/last)
    if 'sorted by alphabetic order' in q or 'alphabetical order' in q:
        names = sorted(set(r[name_col] for r in rows))
        if 'first' in q:
            return names[0]
        elif 'last' in q:
            return names[-1]
    
    # Superlatives: oldest, youngest, heaviest, lightest, tallest, shortest (returning name)
    superlative_map = {
        'oldest': ('age', max), 'youngest': ('age', min),
        'heaviest': ('weight', max), 'lightest': ('weight', min),
        'tallest': ('height', max), 'taller than the other': ('height', max),
    }
    for key, (attr, func) in superlative_map.items():
        if key in q:
            col = get_col_index(attr)
            if col is not None:
                best = func(rows, key=lambda r: numeric(r[col]) or 0)
                return best[name_col]
    
    # "shortest height" -> return value
    if 'shortest height' in q:
        col = get_col_index('height')
        vals = [numeric(r[col]) for r in rows if numeric(r[col]) is not None]
        v = min(vals)
        unit = get_unit(col)
        return (str(int(v)) if v == int(v) else str(v)) + (' ' + unit if unit else '')
    
    # Comparison: "younger/older/taller than <Name>"
    m = re.search(r'(younger|older|taller|shorter|heavier|lighter) than (\w+)', q)
    if m:
        comp_word, ref_name = m.group(1), m.group(2)
        attr_map = {'younger': 'age', 'older': 'age', 'taller': 'height', 'shorter': 'height', 'heavier': 'weight', 'lighter': 'weight'}
        col = get_col_index(attr_map[comp_word])
        ref_row = [r for r in rows if r[name_col] == ref_name]
        if ref_row and col is not None:
            ref_val = numeric(ref_row[0][col])
            less_words = {'younger', 'shorter', 'lighter'}
            if comp_word in less_words:
                result = [r for r in rows if r[name_col] != ref_name and numeric(r[col]) is not None and numeric(r[col]) < ref_val]
            else:
                result = [r for r in rows if r[name_col] != ref_name and numeric(r[col]) is not None and numeric(r[col]) > ref_val]
            if len(result) == 1:
                return result[0][name_col]
    
    # "less than X years old" (which penguin)
    m = re.search(r'less than (\d+\.?\d*)\s*(years? old|year)', q)
    if m:
        val = float(m.group(1))
        col = get_col_index('age')
        result = [r for r in rows if numeric(r[col]) is not None and numeric(r[col]) < val]
        if len(result) == 1:
            return result[0][name_col]
    
    # Lookup: "name of the X m tall penguin" or similar value lookups
    for i, h in enumerate(headers):
        unit = get_unit(i)
        for row in rows:
            val = row[i]
            # Check if the value (with unit) appears in the question
            if unit:
                if val + ' ' + unit in q or val + unit in q:
                    return row[name_col]
            if val in q and i != name_col and len(val) > 1:
                # More specific check
                pattern = re.escape(val)
                if re.search(r'\b' + pattern + r'\b', q):
                    return row[name_col]
    
    return None
