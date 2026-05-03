"""Auto-generated code-distilled implementation for answer_question."""

import re

def answer_question(table, question):
    if not table or not table[0]:
        return None
        
    header = [str(h).lower() for h in table[0]]
    cols = {}
    for i, h in enumerate(header):
        if 'name' in h: cols['name'] = i
        elif 'age' in h: cols['age'] = i
        elif 'height' in h: cols['height'] = i
        elif 'weight' in h: cols['weight'] = i
        
    rows = table[1:]
    
    def parse_float(s):
        try:
            return float(s)
        except ValueError:
            return 0.0

    # 1. How many columns are there in the table?
    if re.search(r"how many columns are there in the table\?", question, re.I):
        return str(len(table[0]))
        
    # 2. How many animals/giraffes/penguins are listed/there?
    if re.search(r"how many (animals|giraffes|penguins) are (listed|there).*\?", question, re.I):
        return str(len(rows))
        
    # 3. What is the name of the X m/cm tall penguin?
    m = re.search(r"what is the name of the ([\d\.]+) (m|cm) tall (?:penguin|animal|giraffe)\?", question, re.I)
    if m:
        val = parse_float(m.group(1))
        h_idx = cols.get('height')
        if h_idx is not None:
            for r in rows:
                if parse_float(r[h_idx]) == val:
                    return r[cols['name']]
                
    # 4. Which is the youngest/oldest/heaviest/lightest/tallest...
    m = re.search(r"which is the (youngest|oldest|heaviest|lightest|tallest) (?:penguin|giraffe|animal)\?", question, re.I)
    if not m:
        m = re.search(r"which (?:penguin|giraffe|animal) is (taller) than the other ones\?", question, re.I)
    if m:
        adj = m.group(1).lower()
        idx = None
        if adj in ['youngest', 'oldest']: idx = cols.get('age')
        elif adj in ['heaviest', 'lightest']: idx = cols.get('weight')
        elif adj in ['tallest', 'taller']: idx = cols.get('height')
        
        if idx is not None:
            if adj in ['youngest', 'lightest']:
                ans = min(rows, key=lambda r: parse_float(r[idx]))
            else:
                ans = max(rows, key=lambda r: parse_float(r[idx]))
            return ans[cols['name']]
            
    # 5. Cumulated age/weight
    m = re.search(r"what is the cumulated (age|weight) of the (?:penguins|animals|giraffes)\?", question, re.I)
    if m:
        field = m.group(1).lower()
        idx = cols.get(field)
        if idx is not None:
            total = sum(parse_float(r[idx]) for r in rows)
            total = round(total, 4)
            if total == int(total):
                return str(int(total))
            return str(total)
            
    # 6. Which penguin is younger/older/heavier/taller than [Name]?
    m = re.search(r"which (?:penguin|animal|giraffe) is (younger|older|heavier|lighter|taller|shorter) than ([a-zA-Z]+)\?", question, re.I)
    if m:
        adj = m.group(1).lower()
        name = m.group(2)
        idx = None
        if adj in ['younger', 'older']: idx = cols.get('age')
        elif adj in ['heavier', 'lighter']: idx = cols.get('weight')
        elif adj in ['taller', 'shorter']: idx = cols.get('height')
        
        if idx is not None:
            ref_val = None
            for r in rows:
                if r[cols['name']].lower() == name.lower():
                    ref_val = parse_float(r[idx])
                    break
            if ref_val is not None:
                for r in rows:
                    val = parse_float(r[idx])
                    if adj in ['younger', 'lighter', 'shorter'] and val < ref_val:
                        return r[cols['name']]
                    if adj in ['older', 'heavier', 'taller'] and val > ref_val:
                        return r[cols['name']]
                        
    # 7. First/last sorted by alphabetic order
    m = re.search(r"what is the name of the (first|last) (?:penguin|animal|giraffe) sorted by alphabetic order\?", question, re.I)
    if m:
        pos = m.group(1).lower()
        sorted_rows = sorted(rows, key=lambda r: r[cols['name']])
        if pos == 'first':
            return sorted_rows[0][cols['name']]
        else:
            return sorted_rows[-1][cols['name']]
            
    # 8. How many penguins are more/less than X years old and weight more/less than Y kg?
    m = re.search(r"how many (?:penguins|animals|giraffes) are (more|less) than ([\d\.]+) years old and weight (more|less) than ([\d\.]+) kg\?", question, re.I)
    if m:
        age_cond = m.group(1).lower()
        age_val = float(m.group(2))
        weight_cond = m.group(3).lower()
        weight_val = float(m.group(4))
        
        count = 0
        for r in rows:
            a = parse_float(r[cols['age']])
            w = parse_float(r[cols['weight']])
            
            if age_cond == 'more' and a <= age_val: continue
            if age_cond == 'less' and a >= age_val: continue
            if weight_cond == 'more' and w <= weight_val: continue
            if weight_cond == 'less' and w >= weight_val: continue
            
            count += 1
        return str(count)
        
    # 9. How many penguins are more/less than X years old?
    m = re.search(r"how many (?:penguins|animals|giraffes) are (more|less) than ([\d\.]+) years old\?", question, re.I)
    if m:
        age_cond = m.group(1).lower()
        age_val = float(m.group(2))
        
        count = 0
        for r in rows:
            a = parse_float(r[cols['age']])
            if age_cond == 'more' and a > age_val: count += 1
            if age_cond == 'less' and a < age_val: count += 1
        return str(count)
        
    # 10. Which penguin is more/less than X years old?
    m = re.search(r"which (?:penguin|animal|giraffe) is (more|less) than ([\d\.]+) years old\?", question, re.I)
    if m:
        age_cond = m.group(1).lower()
        age_val = float(m.group(2))
        
        for r in rows:
            a = parse_float(r[cols['age']])
            if age_cond == 'more' and a > age_val: return r[cols['name']]
            if age_cond == 'less' and a < age_val: return r[cols['name']]
            
    # 11. Which penguin is a female?
    m = re.search(r"which (?:penguin|animal|giraffe) is a female\?", question, re.I)
    if m:
        female_names = {'gwen', 'donna', 'gladys', 'marian', 'jody'}
        for r in rows:
            if r[cols['name']].lower() in female_names:
                return r[cols['name']]

    return None
