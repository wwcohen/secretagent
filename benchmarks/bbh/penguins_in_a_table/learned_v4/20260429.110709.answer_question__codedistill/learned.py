"""Auto-generated code-distilled implementation for answer_question."""

import re

def answer_question(table, question):
    headers = table[0]
    rows = table[1:]
    q = question.lower()
    
    # How many columns
    if 'how many columns' in q:
        return str(len(headers))
    
    # How many animals/penguins are listed
    if re.search(r'how many \w+ are listed', q):
        return str(len(rows))
    
    # Cumulated/sum of a column
    m = re.search(r'cumulated (\w+)', q)
    if m:
        col_name = m.group(1)
        col_idx = None
        for i, h in enumerate(headers):
            if col_name in h.lower():
                col_idx = i
                break
        if col_idx is not None:
            total = sum(float(r[col_idx]) for r in rows)
            return str(int(total)) if total == int(total) else str(total)
    
    # How many with conditions
    m = re.search(r'how many \w+ are (.*)\?', q)
    if m:
        cond_str = m.group(1)
        conditions = re.findall(r'(more|less|greater|fewer) than (\d+\.?\d*) (?:years old|kg|cm|m)', cond_str)
        # Also match "weight more/less than X kg"
        weight_conds = re.findall(r'weight? (more|less) than (\d+\.?\d*)', cond_str)
        count = 0
        for row in rows:
            ok = True
            for comp, val in conditions:
                val = float(val)
                if 'year' in cond_str.split(comp)[0].split('than')[0] or re.search(r'(more|less) than ' + re.escape(str(int(val) if val==int(val) else val)) + r' years', cond_str):
                    age = float(row[headers.index('age')])
                    if comp in ('more', 'greater') and not (age > val): ok = False
                    if comp in ('less', 'fewer') and not (age < val): ok = False
            for comp, val in weight_conds:
                val = float(val)
                wi = next(i for i,h in enumerate(headers) if 'weight' in h)
                w = float(row[wi])
                if comp == 'more' and not (w > val): ok = False
                if comp == 'less' and not (w < val): ok = False
            if ok: count += 1
        return str(count)
    
    # Superlative: oldest, youngest, heaviest, tallest, taller than the other ones
    m = re.search(r'(oldest|youngest|heaviest|lightest|tallest|shortest|taller|heavier|lighter|shorter) (?:than the other ones|\w+)', q)
    if m:
        word = m.group(1)
        col_map = {'oldest':'age','youngest':'age','heaviest':'weight','lightest':'weight','tallest':'height','shortest':'height','taller':'height','heavier':'weight','lighter':'weight','shorter':'height'}
        col_key = col_map.get(word, 'age')
        col_idx = next(i for i,h in enumerate(headers) if col_key in h.lower())
        is_min = word in ('youngest','lightest','shortest','shorter','lighter')
        key_func = min if is_min else max
        best = key_func(rows, key=lambda r: float(r[col_idx]))
        return best[0]
    
    # "younger than X" / "less than X years old" -> find name
    m = re.search(r'younger than (\w+)', q) or re.search(r'less than (\d+) years old', q)
    if m:
        ai = headers.index('age')
        ref = m.group(1)
        if ref.isdigit():
            threshold = float(ref)
            res = [r for r in rows if float(r[ai]) < threshold]
        else:
            ref_row = next(r for r in rows if r[0].lower() == ref.lower())
            res = [r for r in rows if float(r[ai]) < float(ref_row[ai])]
        if len(res) == 1: return res[0][0]
    
    # Lookup by value: "name of the X m tall penguin"
    m = re.search(r'(\d+\.?\d*)\s*(m|cm|kg)\s*tall', q) or re.search(r'(\d+\.?\d*)\s*(m|cm|kg)', q)
    if m:
        val, unit = m.group(1), m.group(2)
        col_idx = next((i for i,h in enumerate(headers) if unit in h), None)
        if col_idx is not None:
            for r in rows:
                if r[col_idx] == val: return r[0]
    
    # Sorted alphabetically first
    if 'alphabetic order' in q:
        sorted_rows = sorted(rows, key=lambda r: r[0])
        return sorted_rows[0][0]
    
    return None
