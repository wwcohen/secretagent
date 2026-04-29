"""Auto-generated code-distilled implementation for answer_finqa."""

def answer_finqa(prompt):
    import re
    import math
    
    # Extract components from the prompt
    # Find context text, table, and question
    
    text_before = ""
    text_after = ""
    table_text = ""
    question = ""
    
    # Parse sections
    sections = prompt.split("## ")
    
    for section in sections:
        if section.startswith("Context (text before table)"):
            text_before = section[len("Context (text before table)"):].strip()
        elif section.startswith("Table"):
            table_text = section[len("Table"):].strip()
        elif section.startswith("Context (text after table)"):
            text_after = section[len("Context (text after table)"):].strip()
        elif section.startswith("Question"):
            question = section[len("Question"):].strip()
    
    if not question:
        # Try alternate parsing
        q_match = re.search(r'(?:##\s*)?Question\s*\n(.*)', prompt, re.DOTALL)
        if q_match:
            question = q_match.group(1).strip()
    
    full_context = text_before + "\n" + text_after
    
    # Parse table into structured data
    def parse_table(t):
        rows = []
        for line in t.strip().split('\n'):
            line = line.strip()
            if line.startswith('|') and not all(c in '|-: ' for c in line):
                cells = [c.strip() for c in line.split('|')]
                cells = [c for c in cells if c != '']
                # skip separator rows
                if cells and not all(re.match(r'^[-:]+$', c) for c in cells):
                    rows.append(cells)
        return rows
    
    table_rows = parse_table(table_text)
    
    def clean_number(s):
        """Extract a number from a string like '$1,234.5' or '(1234)' or '1234%'"""
        if s is None:
            return None
        s = str(s).strip()
        # Handle parenthetical negatives like (1234) or -1234 ( 1234 )
        neg = False
        # Check for patterns like "$ -6129 ( 6129 )" or "-6129 ( 6129 )"
        paren_neg = re.search(r'-\s*[\d,.]+\s*\(\s*[\d,.]+\s*\)', s)
        if paren_neg:
            neg = True
            s = re.sub(r'[()$]', '', s).strip()
            # Take the first number
            nums = re.findall(r'[\d,.]+', s)
            if nums:
                s = nums[0]
        
        # Check for simple parenthetical negatives
        if not paren_neg:
            paren_match = re.match(r'^\$?\s*\(\s*([\d,.]+)\s*\)(.*)$', s)
            if paren_match:
                neg = True
                s = paren_match.group(1)
        
        s = s.replace('$', '').replace(',', '').replace('%', '').replace('€', '')
        s = s.replace('\u2013', '-').replace('\u2014', '-')
        s = s.strip()
        
        if s.startswith('(') and s.endswith(')'):
            neg = True
            s = s[1:-1].strip()
        
        if s.startswith('-'):
            neg = not neg  # toggle
            s = s[1:].strip()
            # If there's still a negative, could be double negative
            if s.startswith('-'):
                neg = not neg
                s = s[1:].strip()
        
        s = s.strip()
        
        try:
            val = float(s)
            return -val if neg else val
        except ValueError:
            return None
    
    def find_value_in_table(row_label, col_label=None, col_idx=None):
        """Find a value in the table by row and column label"""
        if not table_rows or len(table_rows) < 2:
            return None
        
        headers = table_rows[0]
        
        target_col = col_idx
        if col_label and target_col is None:
            col_label_lower = col_label.lower().strip()
            for i, h in enumerate(headers):
                if col_label_lower in h.lower().strip():
                    target_col = i
                    break
        
        row_label_lower = row_label.lower().strip()
        for row in table_rows[1:]:
            if row and row_label_lower in row[0].lower().strip():
                if target_col is not None and target_col < len(row):
                    return clean_number(row[target_col])
                elif len(row) > 1:
                    return clean_number(row[-1])
        return None
    
    def find_row(label):
        """Find a row by partial label match, return the whole row"""
        label_lower = label.lower().strip()
        for row in table_rows:
            if row and label_lower in row[0].lower():
                return row
        return None
    
    def find_col_index(label):
        """Find column index by partial label match"""
        if not table_rows:
            return None
        headers = table_rows[0]
        label_lower = label.lower().strip()
        for i, h in enumerate(headers):
            if label_lower in h.lower():
                return i
        return None
    
    def get_all_numbers_from_text(text):
        """Extract all numbers mentioned in text"""
        # Find patterns like $X.X billion, $X million, etc.
        numbers = []
        # Dollar amounts with billion/million
        for m in re.finditer(r'\$\s*([\d,.]+)\s*(billion|million|thousand)?', text, re.IGNORECASE):
            val = float(m.group(1).replace(',', ''))
            unit = (m.group(2) or '').lower()
            if unit == 'billion':
                val *= 1000
            elif unit == 'thousand':
                val /= 1000
            numbers.append(val)
        # Percentages
        for m in re.finditer(r'([\d,.]+)\s*%', text):
            numbers.append(float(m.group(1).replace(',', '')))
        return numbers
    
    def extract_numbers_from_row(row):
        """Extract all numbers from a table row"""
        nums = []
        for cell in row[1:]:  # skip label
            n = clean_number(cell)
            if n is not None:
                nums.append(n)
        return nums
    
    def format_answer(val, as_percent=False, as_yes_no=False):
        """Format the answer appropriately"""
        if as_yes_no:
            return 'yes' if val else 'no'
        if as_percent:
            # Format percentage
            if abs(val) == int(abs(val)):
                return f"{val:.1f}%"
            elif abs(val * 100) == int(abs(val * 100)):
                return f"{val:.2f}%"
            else:
                return f"{val:.2f}%"
        # General number formatting
        if val == int(val) and abs(val) < 1e10:
            return str(int(val))
        return f"{val:.2f}"
    
    question_lower = question.lower()
    
    # Detect question type
    is_percent_question = any(w in question_lower for w in ['percentage', 'percent', 'portion', 'proportion', 'what percent', '% of'])
    is_change_question = any(w in question_lower for w in ['change', 'increase', 'decrease', 'growth', 'decline', 'grew', 'rose', 'fell'])
    is_yes_no = question_lower.startswith(('is ', 'was ', 'were ', 'are ', 'did ', 'does ', 'do ', 'has ', 'have ', 'will ', 'can ', 'could '))
    is_difference = any(w in question_lower for w in ['difference', 'how much more', 'how much less', 'how much did'])
    is_total = any(w in question_lower for w in ['total', 'sum', 'combined', 'aggregate'])
    is_ratio = any(w in question_lower for w in ['ratio', 'how many times'])
    is_how_much = 'how much' in question_lower
    is_what_was = 'what was' in question_lower or 'what is' in question_lower
    
    # Try to use a simple program-synthesis approach
    # Extract all numbers from question context
    
    def try_answer():
        # Strategy 1: Percentage calculation from table
        if is_percent_question:
            return try_percentage()
        
        # Strategy 2: Yes/No questions
        if is_yes_no:
            return try_yes_no()
        
        # Strategy 3: Change/difference calculations
        if is_change_question:
            return try_change()
        
        # Strategy 4: Simple lookup
        if is_what_was and not is_change_question and not is_percent_question:
            result = try_lookup()
            if result is not None:
                return result
        
        # Strategy 5: Difference
        if is_difference:
            return try_difference()
        
        # Strategy 6: Try general calculation
        return try_general()
    
    def try_percentage():
        """Try to answer percentage questions"""
        # Look for "what percentage of X is Y" pattern
        # or "what portion of X is/was Y"
        
        # Pattern: "what percentage/portion of [total] is/was [part]"
        m = re.search(r'(?:what|the)\s+(?:percentage|percent|portion)\s+(?:of|do|does|did)\s+(.+?)\s+(?:is|was|were|are|represent|constitute|account|make|that is|that was|related to|attributable to)\s+(.+?)[\?]?$', question_lower, re.IGNORECASE)
        
        if not m:
            m = re.search(r'(?:what|the)\s+(?:percentage|percent|portion)\s+(?:of|do|does|did)\s+(.+?)\s+(?:is|was|were|does|do|did)\s+(.+?)[\?]?$', question_lower, re.IGNORECASE)
        
        if m:
            total_label = m.group(1).strip().rstrip('.')
            part_label = m.group(2).strip().rstrip('?').rstrip('.')
            
            # Try to find these in the table
            total_val = None
            part_val = None
            
            # Search table for matching rows
            for row in table_rows[1:]:
                if not row:
                    continue
                row_label = row[0].lower()
                
                # Check total
                total_words = total_label.split()
                if any(w in row_label for w in total_words if len(w) > 3):
                    if 'total' in total_label and 'total' in row_label:
                        nums = extract_numbers_from_row(row)
                        if nums:
                            total_val = nums[-1]  # usually the most recent/relevant
                    elif any(w in row_label for w in total_words if len(w) > 4):
                        nums = extract_numbers_from_row(row)
                        if nums:
                            total_val = nums[-1]
                
                # Check part  
                part_words = part_label.split()
                if any(w in row_label for w in part_words if len(w) > 3):
                    nums = extract_numbers_from_row(row)
                    if nums:
                        part_val = nums[-1]
            
            if total_val and part_val and total_val != 0:
                pct = (part_val / total_val) * 100
                return f"{pct:.2f}%"
        
        # Try simpler patterns - percentage change
        m = re.search(r'(?:percentage|percent)\s+(?:change|increase|decrease|growth|decline)', question_lower)
        if m:
            return try_change()
        
        # Look for two key numbers and compute percentage
        return try_general_percentage()
    
    def try_general_percentage():
        """Try various percentage calculation approaches"""
        # Extract year mentions from question
        years = re.findall(r'20\d{2}|19\d{2}', question_lower)
        
        # Extract key terms from question
        # Try to find relevant row and columns
        if table_rows and len(table_rows) >= 2:
            headers = table_rows[0]
            
            # Find relevant columns by year
            year_cols = {}
            for i, h in enumerate(headers):
                for y in re.findall(r'20\d{2}|19\d{2}', h):
                    year_cols[y] = i
            
            # Look for keywords in question that match row labels
            best_rows = []
            for row in table_rows[1:]:
                if not row:
                    continue
                row_label = row[0].lower()
                # Score by matching words
                score = 0
                q_words = set(re.findall(r'\b\w+\b', question_lower))
                r_words = set(re.findall(r'\b\w+\b', row_label))
                common = q_words & r_words - {'the', 'a', 'an', 'of', 'in', 'is', 'was', 'and', 'to', 'for', 'what', 'how'}
                score = len(common)
                if score > 0:
                    best_rows.append((score, row))
            
            best_rows.sort(key=lambda x: -x[0])
            
            if len(best_rows) >= 2:
                # Might need ratio of two rows
                part_row = best_rows[0][1]
                total_row = best_rows[1][1]
                
                # Determine which is part and which is total
                part_nums = extract_numbers_from_row(part_row)
                total_nums = extract_numbers_from_row(total_row)
                
                if part_nums and total_nums:
                    # Use first year mentioned or last column
                    col_idx = -1
                    if years and year_cols:
                        for y in years:
                            if y in year_cols:
                                ci = year_cols[y] - 1  # adjust for row label
                                if ci < len(part_nums) and ci < len(total_nums):
                                    col_idx = ci
                                    break
                    
                    if col_idx >= 0 and col_idx < len(part_nums) and col_idx < len(total_nums):
                        p = part_nums[col_idx]
                        t = total_nums[col_idx]
                    else:
                        p = part_nums[0] if part_nums else None
                        t = total_nums[0] if total_nums else None
                    
                    if p is not None and t is not None and t != 0:
                        # Determine which is bigger (total should generally be bigger)
                        if abs(t) < abs(p):
                            p, t = t, p
                        pct = (p / t) * 100
                        return f"{pct:.2f}%"
        
        return None
    
    def try_yes_no():
        """Try to answer yes/no questions"""
        # Common patterns: "was X greater/less than Y"
        # "did X increase/decrease"
        
        m = re.search(r'(?:is|was|did|does)\s+.*(?:greater|more|higher|larger|bigger)\s+than', question_lower)
        if m:
            # Need to compare two values
            nums = []
            years = re.findall(r'20\d{2}|19\d{2}', question_lower)
            
            if table_rows and years:
                headers = table_rows[0]
                year_cols = {}
                for i, h in enumerate(headers):
                    for y in re.findall(r'20\d{2}|19\d{2}', h):
                        year_cols[y] = i
                
                # Find relevant row
                for row in table_rows[1:]:
                    if not row:
                        continue
                    row_label = row[0].lower()
                    q_words = set(re.findall(r'\b\w+\b', question_lower))
                    r_words = set(re.findall(r'\b\w+\b', row_label))
                    common = q_words & r_words - {'the', 'a', 'an', 'of', 'in', 'is', 'was', 'and', 'to', 'for', 'what', 'how', 'did', 'does'}
                    if common:
                        for y in years:
                            if y in year_cols:
                                ci = year_cols[y]
                                if ci < len(row):
                                    v = clean_number(row[ci])
                                    if v is not None:
                                        nums.append((y, v))
                        break
            
            if len(nums) >= 2:
                # First year mentioned compared to second
                if nums[0][1] > nums[1][1]:
                    return 'yes'
                else:
                    return 'no'
        
        m = re.search(r'(?:is|was|did|does)\s+.*(?:less|lower|smaller|fewer)\s+than', question_lower)
        if m:
            nums = []
            years = re.findall(r'20\d{2}|19\d{2}', question_lower)
            
            if table_rows and years:
                headers = table_rows[0]
                year_cols = {}
                for i, h in enumerate(headers):
                    for y in re.findall(r'20\d{2}|19\d{2}', h):
                        year_cols[y] = i
                
                for row in table_rows[1:]:
                    if not row:
                        continue
                    row_label = row[0].lower()
                    q_words = set(re.findall(r'\b\w+\b', question_lower))
                    r_words = set(re.findall(r'\b\w+\b', row_label))
                    common = q_words & r_words - {'the', 'a', 'an', 'of', 'in', 'is', 'was', 'and', 'to', 'for', 'what', 'how', 'did', 'does'}
                    if common:
                        for y in years:
                            if y in year_cols:
                                ci = year_cols[y]
                                if ci < len(row):
                                    v = clean_number(row[ci])
                                    if v is not None:
                                        nums.append((y, v))
                        break
            
            if len(nums) >= 2:
                if nums[0][1] < nums[1][1]:
                    return 'yes'
                else:
                    return 'no'
        
        # "did X increase/decrease from Y to Z"
        m = re.search(r'did\s+.*(?:increase|grow|rise)', question_lower)
        if m:
            years = re.findall(r'20\d{2}|19\d{2}', question_lower)
            if table_rows and len(years) >= 2:
                headers = table_rows[0]
                year_cols = {}
                for i, h in enumerate(headers):
                    for y in re.findall(r'20\d{2}|19\d{2}', h):
                        year_cols[y] = i
                
                for row in table_rows[1:]:
                    if not row:
                        continue
                    row_label = row[0].lower()
                    q_words = set(re.findall(r'\b\w+\b', question_lower))
                    r_words = set(re.findall(r'\b\w+\b', row_label))
                    common = q_words & r_words - {'the', 'a', 'an', 'of', 'in', 'is', 'was', 'and', 'to', 'for', 'what', 'how', 'did', 'does', 'increase', 'grow', 'from'}
                    if len(common) >= 1:
                        vals = []
                        for y in years:
                            if y in year_cols:
                                ci = year_cols[y]
                                if ci < len(row):
                                    v = clean_number(row[ci])
                                    if v is not None:
                                        vals.append((y, v))
                        if len(vals) >= 2:
                            # Check if increased from first to last year
                            if int(vals[-1][0]) > int(vals[0][0]):
                                return 'yes' if vals[-1][1] > vals[0][1] else 'no'
                            else:
                                return 'yes' if vals[0][1] > vals[-1][1] else 'no'
        
        # Generic yes/no - try to evaluate the condition
        # For "was the total ... positive/negative"
        if 'positive' in question_lower or 'negative' in question_lower:
            # Find relevant value
            for row in table_rows[1:]:
                if not row:
                    continue
                row_label = row[0].lower()
                q_words = set(re.findall(r'\b\w+\b', question_lower))
                r_words = set(re.findall(r'\b\w+\b', row_label))
                common = q_words & r_words - {'the', 'a', 'an', 'of', 'in', 'is', 'was', 'and', 'to', 'for', 'what', 'how', 'positive', 'negative'}
                if len(common) >= 2:
                    nums = extract_numbers_from_row(row)
                    if nums:
                        val = nums[-1]
                        if 'positive' in question_lower:
                            return 'yes' if val > 0 else 'no'
                        else:
                            return 'yes' if val < 0 else 'no'
        
        return try_general()
    
    def try_change():
        """Calculate change between periods"""
        years = re.findall(r'20\d{2}|19\d{2}', question_lower)
        
        if not years:
            years = re.findall(r'20\d{2}|19\d{2}', question.lower())
        
        is_pct_change = any(w in question_lower for w in ['percentage', 'percent', '%'])
        
        if table_rows and len(years) >= 2:
            headers = table_rows[0]
            year_cols = {}
            for i, h in enumerate(headers):
                for y in re.findall(r'20\d{2}|19\d{2}', h):
                    year_cols[y] = i
            
            # Find relevant row
            best_row = None
            best_score = 0
            
            for row in table_rows[1:]:
                if not row:
                    continue
                row_label = row[0].lower()
                q_words = set(re.findall(r'\b[a-z]+\b', question_lower))
                r_words = set(re.findall(r'\b[a-z]+\b', row_label))
                stop_words = {'the', 'a', 'an', 'of', 'in', 'is', 'was', 'and', 'to', 'for', 'what', 
                            'how', 'did', 'does', 'from', 'between', 'change', 'percentage', 'percent',
                            'increase', 'decrease', 'growth', 'much', 'total', 'net'}
                common = q_words & r_words - stop_words
                score = len(common)
                if 'total' in question_lower and 'total' in row_label:
                    score += 2
                if score > best_score:
                    best_score = score
                    best_row = row
            
            if best_row and len(years) >= 2:
                y1, y2 = years[0], years[1]
                # Get values for the two years
                v1, v2 = None, None
                if y1 in year_cols:
                    ci = year_cols[y1]
                    if ci < len(best_row):
                        v1 = clean_number(best_row[ci])
                if y2 in year_cols:
                    ci = year_cols[y2]
                    if ci < len(best_row):
                        v2 = clean_number(best_row[ci])
                
                if v1 is not None and v2 is not None:
                    if is_pct_change:
                        # Determine base year (earlier year for "from X to Y")
                        # Usually percentage change = (new - old) / old * 100
                        if int(y1) < int(y2):
                            base = v1
                            new = v2
                        else:
                            base = v2
                            new = v1
                        
                        if 'from' in question_lower:
                            # "from 2010 to 2011" means base is 2010
                            fm = re.search(r'from\s+(\d{4})', question_lower)
                            tm = re.search(r'to\s+(\d{4})', question_lower)
                            if fm and tm:
                                fy = fm.group(1)
                                ty = tm.group(1)
                                if fy in year_cols and ty in year_cols:
                                    bci = year_cols[fy]
                                    nci = year_cols[ty]
                                    if bci < len(best_row) and nci < len(best_row):
                                        base = clean_number(best_row[bci])
                                        new = clean_number(best_row[nci])
                        
                        if base and base != 0:
                            pct = ((new - base) / abs(base)) * 100
                            return f"{pct:.2f}%"
                    else:
                        # Absolute change
                        if int(y1) < int(y2):
                            change = v2 - v1
                        else:
                            change = v1 - v2
                        if change == int(change):
                            return str(int(change))
                        return f"{change:.2f}"
        
        return None
    
    def try_lookup():
        """Simple value lookup from table"""
        years = re.findall(r'20\d{2}|19\d{2}', question_lower)
        
        if table_rows:
            headers = table_rows[0]
            year_cols = {}
            for i, h in enumerate(headers):
                for y in re.findall(r'20\d{2}|19\d{2}', h):
                    year_cols[y] = i
            
            best_row = None
            best_score = 0
            
            for row in table_rows[1:]:
                if not row:
                    continue
                row_label = row[0].lower()
                q_words = set(re.findall(r'\b[a-z]+\b', question_lower))
                r_words = set(re.findall(r'\b[a-z]+\b', row_label))
                stop_words = {'the', 'a', 'an', 'of', 'in', 'is', 'was', 'and', 'to', 'for', 'what',
                            'how', 'much', 'value', 'amount'}
                common = q_words & r_words - stop_words
                score = len(common)
                if score > best_score:
                    best_score = score
                    best_row = row
            
            if best_row and best_score > 0:
                target_col = None
                if years:
                    for y in years:
                        if y in year_cols:
                            target_col = year_cols[y]
                            break
                
                if target_col is not None and target_col < len(best_row):
                    val = clean_number(best_row[target_col])
                    if val is not None:
                        if val == int(val):
                            return str(int(val))
                        return f"{val:.2f}"
                else:
                    # Return last numeric column
                    nums = extract_numbers_from_row(best_row)
                    if nums:
                        val = nums[-1]
                        if val == int(val):
                            return str(int(val))
                        return f"{val:.2f}"
        
        return None
    
    def try_difference():
        """Calculate difference between two values"""
        return try_change()
    
    def try_general():
        """General fallback approach"""
        # Try percentage first if relevant keywords
        if is_percent_question:
            result = try_general_percentage()
            if result:
                return result
        
        # Try change
        if is_change_question:
            result = try_change()
            if result:
                return result
        
        # Try lookup
        result = try_lookup()
        if result:
            return result
        
        return None
    
    result = try_answer()
    
    if result is not None:
        return str(result)
    
    return None
