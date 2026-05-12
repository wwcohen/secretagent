"""Auto-generated end-to-end implementation for answer_finqa."""

import re
import math

def answer_finqa(question_text):
    """Answer a numerical reasoning question over a financial report excerpt."""
    
    def parse_input(text):
        """Parse the input into context_before, table, context_after, and question."""
        # Extract sections
        parts = text.split('## ')
        
        context_before = ""
        table_text = ""
        context_after = ""
        question = ""
        
        for part in parts:
            if part.startswith('Context (text before table)'):
                context_before = part[len('Context (text before table)'):].strip()
            elif part.startswith('Table'):
                table_text = part[len('Table'):].strip()
            elif part.startswith('Context (text after table)'):
                context_after = part[len('Context (text after table)'):].strip()
            elif part.startswith('Question'):
                question = part[len('Question'):].strip()
        
        # Parse table
        table = parse_table(table_text)
        
        # Clean question - remove the reply instruction
        q_lines = question.split('\n')
        clean_q = []
        for line in q_lines:
            if line.strip().startswith('Reply with only'):
                break
            clean_q.append(line)
        question = '\n'.join(clean_q).strip()
        
        return context_before, table, context_after, question
    
    def parse_table(table_text):
        """Parse markdown table into list of lists."""
        lines = table_text.strip().split('\n')
        rows = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('|') == False:
                continue
            # Skip separator lines
            if re.match(r'^\|[\s\-:|]+\|$', line):
                continue
            cells = [c.strip() for c in line.split('|')]
            # Remove empty first and last from split
            cells = [c for i, c in enumerate(cells) if not (i == 0 and c == '') and not (i == len(cells)-1 and c == '')]
            if cells:
                rows.append(cells)
        return rows
    
    def clean_number(s):
        """Extract a number from a string."""
        if s is None:
            return None
        s = str(s).strip()
        
        # Handle parenthetical negatives like "-26 ( 26 )" or "( 26 )" or "-2080 ( 2080 )"
        # Pattern: negative with parenthetical confirmation
        m = re.match(r'^[−\-]\s*\$?\s*([\d,]+\.?\d*)\s*\(\s*[\d,]+\.?\d*\s*\)', s)
        if m:
            return -float(m.group(1).replace(',', ''))
        
        # Pattern: just parenthetical like "( 26 )"
        m = re.match(r'^\(\s*\$?\s*([\d,]+\.?\d*)\s*\)', s)
        if m:
            return -float(m.group(1).replace(',', ''))
        
        # Remove dollar signs, percent signs
        s = s.replace('$', '').replace('€', '').replace('£', '').strip()
        
        # Handle percentage
        pct = False
        if s.endswith('%'):
            s = s.replace('%', '').strip()
            pct = True
        # Handle patterns like "27.5% ( 27.5 % )"
        m = re.match(r'([\d,]+\.?\d*)\s*%\s*\(\s*[\d,]+\.?\d*\s*%\s*\)', s)
        if m:
            return float(m.group(1).replace(',', ''))
        
        # Remove any remaining parenthetical patterns
        s = re.sub(r'\s*\(.*?\)', '', s).strip()
        
        # Handle negative sign
        neg = False
        if s.startswith('-') or s.startswith('−'):
            neg = True
            s = s[1:].strip()
        
        # Remove commas
        s = s.replace(',', '').strip()
        
        # Try to parse
        try:
            val = float(s)
            if neg:
                val = -val
            return val
        except (ValueError, TypeError):
            return None
    
    def find_value_in_table(table, row_key, col_key=None):
        """Find a value in the table by row and column keywords."""
        if not table or len(table) < 2:
            return None
        
        header = table[0]
        
        # Try to find matching row and column
        for row in table[1:]:
            if len(row) < 2:
                continue
            row_label = row[0].lower().strip()
            if row_key.lower() in row_label or row_label in row_key.lower():
                if col_key:
                    for j, h in enumerate(header):
                        if j < len(row) and (col_key.lower() in h.lower() or h.lower() in col_key.lower()):
                            return clean_number(row[j])
                    # Try matching column by content
                    if len(row) > 1:
                        return clean_number(row[-1])
                else:
                    if len(row) > 1:
                        return clean_number(row[1])
        return None
    
    def get_all_numbers_from_text(text):
        """Extract all numbers from text."""
        numbers = {}
        # Find patterns like "$ 123.4 million" or "123.4 billion"
        patterns = re.findall(r'\$?\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?', text.lower())
        for val, unit in patterns:
            try:
                v = float(val.replace(',', ''))
                if unit == 'billion':
                    v *= 1000
                elif unit == 'thousand':
                    v /= 1000
                numbers[val] = v
            except:
                pass
        return numbers
    
    def build_value_dict(table, context_before, context_after):
        """Build a dictionary of named values from the table and context."""
        values = {}
        if not table:
            return values
        
        header = table[0]
        for row in table:
            if len(row) >= 2:
                label = row[0].strip().lower()
                for j in range(1, len(row)):
                    col_label = header[j].strip().lower() if j < len(header) else str(j)
                    val = clean_number(row[j])
                    if val is not None:
                        key = (label, col_label)
                        values[key] = val
                        # Also store with just label if only one data column
                        if len(row) == 2:
                            values[(label, '')] = val
        
        return values

    def extract_years_from_header(header):
        """Extract years from table header."""
        years = []
        for h in header:
            # Find 4-digit years
            found = re.findall(r'((?:19|20)\d{2})', h)
            if found:
                years.append((h, int(found[-1])))  # Use last year found
        return years
    
    def find_table_value(table, row_keywords, year=None, col_idx=None):
        """Find a value in table matching row keywords and optionally a year or column index."""
        if not table or len(table) < 2:
            return None
        
        header = table[0]
        
        # Find column index for year
        target_col = col_idx
        if year is not None and target_col is None:
            for j, h in enumerate(header):
                if str(year) in h:
                    target_col = j
                    break
        
        # Find matching row
        for row in table[1:]:
            if len(row) < 2:
                continue
            row_label = row[0].lower().strip()
            
            # Check if all keywords match
            match = True
            for kw in row_keywords:
                if kw.lower() not in row_label:
                    match = False
                    break
            
            if match:
                if target_col is not None and target_col < len(row):
                    return clean_number(row[target_col])
                elif target_col is None and len(row) >= 2:
                    # Return first data column
                    return clean_number(row[1])
        
        return None
    
    def find_best_row_match(table, keywords):
        """Find the best matching row for given keywords."""
        if not table:
            return None, None
        
        best_score = -1
        best_row_idx = None
        
        for i, row in enumerate(table):
            if len(row) < 2:
                continue
            label = row[0].lower().strip()
            score = 0
            for kw in keywords:
                if kw.lower() in label:
                    score += len(kw)
            if score > best_score:
                best_score = score
                best_row_idx = i
        
        if best_score > 0:
            return best_row_idx, table[best_row_idx]
        return None, None
    
    def find_col_for_year(header, year):
        """Find column index for a given year."""
        year_str = str(year)
        for j, h in enumerate(header):
            if year_str in h:
                return j
        return None
    
    def extract_numbers_near_keyword(text, keyword):
        """Extract numbers near a keyword in text."""
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        idx = text_lower.find(keyword_lower)
        if idx == -1:
            return []
        
        # Look in a window around the keyword
        start = max(0, idx - 100)
        end = min(len(text), idx + len(keyword) + 200)
        snippet = text[start:end]
        
        # Find dollar amounts
        amounts = re.findall(r'\$\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?', snippet.lower())
        results = []
        for val, unit in amounts:
            try:
                v = float(val.replace(',', ''))
                if unit == 'billion':
                    v *= 1000
                elif unit == 'thousand':
                    v /= 1000
                results.append(v)
            except:
                pass
        
        # Also find plain numbers
        plain = re.findall(r'(?<!\d)([\d,]+\.?\d+)(?!\d)', snippet)
        for val in plain:
            try:
                v = float(val.replace(',', ''))
                if v not in results:
                    results.append(v)
            except:
                pass
        
        return results
    
    def solve(context_before, table, context_after, question):
        """Solve the financial reasoning question."""
        q = question.lower().strip()
        full_context = context_before + '\n' + context_after
        
        header = table[0] if table else []
        
        # Extract years from header
        year_cols = extract_years_from_header(header)
        years_in_header = [y for _, y in year_cols]
        
        # Also extract years from question
        q_years = re.findall(r'(?:19|20)\d{2}', q)
        q_years = [int(y) for y in q_years]
        
        # Detect date patterns like "12/31/2016" or "december 31, 2016"
        date_years = re.findall(r'(?:12/31/|december\s+31\s*,?\s*)((?:19|20)\d{2})', q)
        date_years = [int(y) for y in date_years]
        if date_years:
            q_years = date_years if not q_years else q_years
        
        # Try to understand the question type
        
        # PERCENTAGE CHANGE questions
        pct_change_patterns = [
            r'(?:what\s+(?:is|was)\s+the\s+)?percent(?:age)?\s+(?:change|increase|decrease|growth|decline)',
            r'(?:by\s+)?how\s+much\s+did\s+.*\s+(?:change|increase|decrease|grow)',
            r'what\s+(?:is|was)\s+the\s+(?:percentage|percent)\s+(?:change|increase|decrease)',
        ]
        
        is_pct_change = any(re.search(p, q) for p in pct_change_patterns)
        
        # RATIO / PORTION / PERCENTAGE OF questions
        portion_patterns = [
            r'what\s+(?:portion|percent(?:age)?|proportion|share)\s+of\s+(?:the\s+)?(?:total\s+)?(.+?)\s+(?:is|was|are|were|comes?\s+from|(?:is\s+)?(?:related|dedicated|due|attributable|comprised|associated|incurred)\s+(?:to|from|of|with)?)\s+(.+)',
            r'what\s+(?:percent(?:age)?)\s+of\s+(.+?)\s+(?:is|was|are|were)\s+(?:comprised\s+of\s+)?(.+)',
        ]
        
        is_portion = any(re.search(p, q) for p in portion_patterns)
        
        # AVERAGE questions
        is_average = 'average' in q and ('what' in q or 'considering' in q)
        
        # DIFFERENCE / CHANGE questions
        is_difference = any(w in q for w in ['difference', 'change in', 'net change', 'how much did'])
        
        # ROI questions
        is_roi = 'roi' in q or 'return on investment' in q
        
        # RETURN ON questions (like return on total assets)
        is_return_on = 'return on' in q and 'roi' not in q
        
        # RATIO questions
        is_ratio = 'ratio' in q and 'what' in q
        
        # CUMULATIVE RETURN questions
        is_cumulative_return = 'cumulative' in q and 'return' in q
        
        # TOTAL questions (sum)
        is_total = 'total' in q and ('what' in q or 'how much' in q)
        
        # Try to find relevant row keywords from question
        def extract_row_keywords(question_text):
            """Extract potential row identifiers from the question."""
            # Remove common question words
            stop_words = {'what', 'is', 'the', 'was', 'were', 'are', 'of', 'in', 'for', 
                         'from', 'to', 'and', 'a', 'an', 'how', 'much', 'did', 'does',
                         'percentage', 'percent', 'change', 'between', 'during', 'total',
                         'average', 'ratio', 'compared', 'increase', 'decrease', 'portion',
                         'related', 'dedicated', 'due', 'that', 'with', 'by', 'as', 'on',
                         'at', 'its', 'this', 'these', 'those', 'year', 'years', 'ended',
                         'ending', 'december', 'march', 'june', 'september', 'january',
                         'february', 'would', 'have', 'been', 'all', 'our', 'their', 'it',
                         'over', 'under', 'five', 'period', 'periods', 'quarter', 'which',
                         'if', 'not', 'net', 'per', 'each'}
            
            words = re.findall(r'\b[a-z]+\b', question_text.lower())
            keywords = [w for w in words if w not in stop_words and len(w) > 2]
            return keywords
        
        # Helper to get value from table for a concept and year
        def get_value(row_search_terms, year=None, col_idx=None):
            """Get a value from the table."""
            if not table or len(table) < 2:
                return None
            
            header_row = table[0]
            
            # Determine target column
            target_col = col_idx
            if year is not None and target_col is None:
                for j, h in enumerate(header_row):
                    if str(year) in h:
                        target_col = j
                        break
            
            # Search for matching row
            best_match = None
            best_score = 0
            
            for i, row in enumerate(table[1:], 1):
                if len(row) < 2:
                    continue
                label = row[0].lower().strip()
                
                score = 0
                for term in row_search_terms:
                    term_lower = term.lower()
                    if term_lower in label:
                        score += len(term_lower)
                
                if score > best_score:
                    best_score = score
                    best_match = row
            
            if best_match is not None and best_score > 0:
                if target_col is not None and target_col < len(best_match):
                    return clean_number(best_match[target_col])
                elif len(best_match) >= 2:
                    # If no specific column, try to return appropriate one
                    for j in range(1, len(best_match)):
                        v = clean_number(best_match[j])
                        if v is not None:
                            return v
            
            return None
        
        def get_row_values(row_search_terms):
            """Get all values for a matching row."""
            if not table or len(table) < 2:
                return {}
            
            header_row = table[0]
            best_match = None
            best_score = 0
            
            for i, row in enumerate(table[1:], 1):
                if len(row) < 2:
                    continue
                label = row[0].lower().strip()
                
                score = 0
                for term in row_search_terms:
                    if term.lower() in label:
                        score += len(term.lower())
                
                if score > best_score:
                    best_score = score
                    best_match = row
            
            if best_match is not None and best_score > 0:
                result = {}
                for j in range(len(best_match)):
                    col_name = header_row[j] if j < len(header_row) else str(j)
                    val = clean_number(best_match[j])
                    if val is not None:
                        result[col_name] = val
                        # Also store by year if year found in header
                        year_match = re.findall(r'((?:19|20)\d{2})', col_name)
                        if year_match:
                            result[int(year_match[-1])] = val
                return result
            return {}
        
        # ================================================================
        # HANDLE SPECIFIC QUESTION PATTERNS
        # ================================================================
        
        # --- Percentage change ---
        if is_pct_change and len(q_years) >= 2:
            year1 = min(q_years)
            year2 = max(q_years)
            
            # Find the concept being measured
            row_kw = extract_row_keywords(q)
            
            # Try to find values for both years
            val1 = get_value(row_kw, year1)
            val2 = get_value(row_kw, year2)
            
            if val1 is not None and val2 is not None and val1 != 0:
                result = (val2 - val1) / abs(val1)
                return result
            
            # Try with context
            nums_context = extract_numbers_near_keyword(full_context, str(year1))
            nums_context2 = extract_numbers_near_keyword(full_context, str(year2))
        
        # --- ROI (return on investment in stock) ---
        if is_roi:
            if len(q_years) >= 2:
                year1 = min(q_years)
                year2 = max(q_years)
                
                # Look for values in the stock performance table
                # Find the entity row
                row_kw = extract_row_keywords(q)
                vals = get_row_values(row_kw)
                
                v1 = vals.get(year1)
                v2 = vals.get(year2)
                
                if v1 is not None and v2 is not None and v1 != 0:
                    return (v2 - v1) / v1
        
        # --- Return on assets/equity ---
        if is_return_on and not is_cumulative_return:
            # "return on total assets during 2014" -> net income / total assets
            if len(q_years) >= 1:
                year = q_years[0]
                
                # Determine numerator and denominator
                if 'asset' in q:
                    num_kw = ['net earnings', 'net income', 'net loss']
                    den_kw = ['total assets']
                elif 'equity' in q:
                    num_kw = ['net earnings', 'net income']
                    den_kw = ['equity', 'stockholder']
                else:
                    num_kw = ['net earnings', 'net income']
                    den_kw = extract_row_keywords(q)
                
                numerator = None
                for kw_set in num_kw:
                    numerator = get_value(kw_set.split(), year)
                    if numerator is not None:
                        break
                
                denominator = None
                for kw_set in den_kw:
                    denominator = get_value(kw_set.split() if isinstance(kw_set, str) else [kw_set], year)
                    if denominator is not None:
                        break
                
                if numerator is not None and denominator is not None and denominator != 0:
                    return numerator / denominator
        
        # --- Cumulative return ---
        if is_cumulative_return or ('cumulative' in q and 'return' in q):
            if len(q_years) >= 1:
                end_year = max(q_years)
                
                row_kw = extract_row_keywords(q)
                vals = get_row_values(row_kw)
                
                end_val = vals.get(end_year)
                
                if end_val is not None:
                    # Cumulative return from $100 base
                    start_val = 100.0
                    # Check if there's a start value
                    if len(q_years) >= 2:
                        start_year = min(q_years)
                        sv = vals.get(start_year)
                        if sv is not None:
                            start_val = sv
                    
                    return (end_val - start_val) / start_val
        
        # --- Portion/percentage of ---
        if is_portion:
            # Find what we're looking at portion of (denominator) and what the numerator is
            for pattern in portion_patterns:
                m = re.search(pattern, q)
                if m:
                    denom_text = m.group(1).strip()
                    num_text = m.group(2).strip()
                    
                    # Remove trailing question marks, year references
                    num_text = re.sub(r'\?.*$', '', num_text).strip()
                    num_text = re.sub(r'(?:as\s+of|in|during|for)\s+(?:the\s+)?(?:year\s+ended?\s+)?(?:december|march|june|september)\s+\d+\s*,?\s*\d{4}', '', num_text).strip()
                    
                    denom_kw = extract_row_keywords(denom_text)
                    num_kw = extract_row_keywords(num_text)
                    
                    year = q_years[0] if q_years else None
                    
                    # Get denominator value
                    denom_val = get_value(denom_kw, year)
                    num_val = get_value(num_kw, year)
                    
                    if denom_val is not None and num_val is not None and denom_val != 0:
                        return abs(num_val) / abs(denom_val)
                    break
        
        # --- "what percent of X is Y" or "Y as a percent of X" ---
        pct_of_match = re.search(r'what\s+percent(?:age)?\s+of\s+(.+?)\s+(?:is|was|are|were|does)\s+(.+?)[\?]?$', q)
        if not pct_of_match:
            pct_of_match = re.search(r'what\s+percent(?:age)?\s+of\s+(.+?)\s+(?:is|was)\s+(?:comprised\s+of\s+|dedicated\s+to\s+|related\s+to\s+|associated\s+with\s+|attributable\s+to\s+|due\s+(?:to|in)\s+)?(.+?)[\?]?$', q)
        
        if pct_of_match and not is_pct_change:
            denom_text = pct_of_match.group(1).strip()
            num_text = pct_of_match.group(2).strip()
            
            # Clean up year references
            for yt in [r'as\s+of\s+december\s+31\s*,?\s*\d{4}', r'in\s+\d{4}', r'during\s+\d{4}', r'for\s+\d{4}']:
                denom_text = re.sub(yt, '', denom_text).strip()
                num_text = re.sub(yt, '', num_text).strip()
            
            denom_kw = extract_row_keywords(denom_text)
            num_kw = extract_row_keywords(num_text)
            
            year = q_years[0] if q_years else None
            
            denom_val = get_value(denom_kw, year)
            num_val = get_value(num_kw, year)
            
            if denom_val is not None and num_val is not None and denom_val != 0:
                return abs(num_val) / abs(denom_val)
        
        # --- Average ---
        if is_average:
            row_kw = extract_row_keywords(q)
            
            if q_years:
                values = []
                for y in sorted(set(q_years)):
                    v = get_value(row_kw, y)
                    if v is not None:
                        values.append(v)
                
                if not values:
                    # Try getting all values in the row
                    vals_dict = get_row_values(row_kw)
                    for y in sorted(set(q_years)):
                        if y in vals_dict:
                            values.append(vals_dict[y])
                
                if values:
                    return sum(values) / len(values)
            
            # If years span a range ("from 2010 to 2012" or "2014-2016")
            range_match = re.search(r'(?:from\s+)?(\d{4})\s*(?:to|-|through|and)\s*(\d{4})', q)
            if range_match:
                y1 = int(range_match.group(1))
                y2 = int(range_match.group(2))
                values = []
                for y in range(y1, y2 + 1):
                    v = get_value(row_kw, y)
                    if v is not None:
                        values.append(v)
                if values:
                    return sum(values) / len(values)
            
            # "considering the years 2014-2016" pattern
            range_match2 = re.search(r'(?:years?\s+)?(\d{4})\s*[-–]\s*(\d{4})', q)
            if range_match2:
                y1 = int(range_match2.group(1))
                y2 = int(range_match2.group(2))
                values = []
                for y in range(y1, y2 + 1):
                    v = get_value(row_kw, y)
                    if v is not None:
                        values.append(v)
                if not values:
                    # Try context
                    pass
                if values:
                    return sum(values) / len(values)
            
            # Average of specific values mentioned
            if 'high' in q and 'low' in q:
                # Average of high and low
                high_val = get_value(['high'], q_years[0] if q_years else None)
                low_val = get_value(['low'], q_years[0] if q_years else None)
                if high_val is not None and low_val is not None:
                    return (high_val + low_val) / 2
        
        # --- Difference/change ---
        if is_difference and not is_pct_change:
            if len(q_years) >= 2:
                year1 = min(q_years)
                year2 = max(q_years)
                
                row_kw = extract_row_keywords(q)
                val1 = get_value(row_kw, year1)
                val2 = get_value(row_kw, year2)
                
                if val1 is not None and val2 is not None:
                    return val2 - val1
        
        # --- Total/sum questions ---
        if is_total and not is_portion and not is_pct_change:
            row_kw = extract_row_keywords(q)
            if q_years:
                values = []
                for y in sorted(set(q_years)):
                    v = get_value(row_kw, y)
                    if v is not None:
                        values.append(v)
                if values and len(values) > 1:
                    return sum(values)
            
            # Range of years
            range_match = re.search(r'(\d{4})\s*(?:to|-|through)\s*(\d{4})', q)
            if range_match:
                y1 = int(range_match.group(1))
                y2 = int(range_match.group(2))
                values = []
                for y in range(y1, y2 + 1):
                    v = get_value(row_kw, y)
                    if v is not None:
                        values.append(v)
                if values and len(values) > 1:
                    return sum(values)
        
        # --- "What was the X in YEAR" ---
        simple_value_match = re.search(r'what\s+(?:is|was|were)\s+(?:the\s+)?(.+?)(?:\s+in\s+|\s+for\s+|\s+during\s+|\s+as\s+of\s+)(?:the\s+)?(?:year\s+(?:ended?\s+)?)?(?:fiscal\s+)?(?:december\s+31\s*,?\s*)?\s*(\d{4})', q)
        
        # --- Handle special patterns from context ---
        
        # Pattern: "expense X as a percentage of Y"
        expense_pct = re.search(r'(.+?)\s+as\s+a\s+percentage\s+of\s+(.+)', q)
        if expense_pct:
            num_text = expense_pct.group(1).strip()
            den_text = expense_pct.group(2).strip()
            
            num_kw = extract_row_keywords(num_text)
            den_kw = extract_row_keywords(den_text)
            
            year = q_years[0] if q_years else None
            
            num_val = get_value(num_kw, year)
            den_val = get_value(den_kw, year)
            
            if num_val is not None and den_val is not None and den_val != 0:
                return num_val / den_val
        
        # --- Handle "in 2008 what was the percent of total X that was associated with Y" ---
        pct_assoc = re.search(r'what\s+(?:was|is)\s+the\s+percent\s+of\s+(?:the\s+)?(.+?)\s+that\s+was\s+(?:associated\s+with|related\s+to|due\s+to|from)\s+(.+)', q)
        if pct_assoc:
            den_text = pct_assoc.group(1).strip()
            num_text = pct_assoc.group(2).strip()
            
            den_kw = extract_row_keywords(den_text)
            num_kw = extract_row_keywords(num_text)
            
            year = q_years[0] if q_years else None
            
            den_val = get_value(den_kw, year)
            num_val = get_value(num_kw, year)
            
            if den_val is not None and num_val is not None and den_val != 0:
                return abs(num_val) / abs(den_val)
        
        # --- Try general approach: extract numbers from context and compute ---
        
        # Look for specific number patterns in context  
        # "stock based compensation expense was $ 37 million"
        # "$ 15 million of expense"
        
        # Handle questions about values mentioned in context
        context_numbers = {}
        for sent in re.split(r'[.\n]', full_context):
            sent = sent.strip()
            if not sent:
                continue
            amounts = re.findall(r'\$\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?', sent.lower())
            for val, unit in amounts:
                try:
                    v = float(val.replace(',', ''))
                    if unit == 'billion':
                        v *= 1000
                    elif unit == 'thousand':
                        v /= 1000
                    context_numbers[v] = sent
                except:
                    pass
        
        # ================================================================
        # FALLBACK: Try harder with more specific pattern matching
        # ================================================================
        
        # "what is the expense which relates to X as a percentage of Y"
        if 'percentage' in q or 'percent' in q:
            # Try to find two numbers in the context that match the question
            # Look for numerator and denominator keywords
            pass
        
        # Handle "by how much did X increase from YEAR to YEAR"
        increase_match = re.search(r'(?:by\s+)?how\s+much\s+did\s+(?:the\s+)?(.+?)\s+(?:increase|decrease|change|grow|decline)\s+(?:from\s+)?(\d{4})\s+to\s+(\d{4})', q)
        if increase_match:
            concept = increase_match.group(1)
            year1 = int(increase_match.group(2))
            year2 = int(increase_match.group(3))
            
            row_kw = extract_row_keywords(concept)
            val1 = get_value(row_kw, year1)
            val2 = get_value(row_kw, year2)
            
            if val1 is not None and val2 is not None:
                diff = val2 - val1
                if val1 != 0:
                    return diff / abs(val1)
                return diff
        
        # --- Handle questions asking about specific line items and computing ratios/changes ---
        
        # Try a more aggressive approach: parse the question for numbers and operations
        
        # "what is the net change in X from YEAR to YEAR"
        net_change = re.search(r'(?:net\s+)?change\s+in\s+(?:the\s+)?(.+?)(?:\s+from\s+|\s+between\s+)(\d{4})\s+(?:to|and)\s+(\d{4})', q)
        if net_change:
            concept = net_change.group(1)
            year1 = int(net_change.group(2))
            year2 = int(net_change.group(3))
            
            row_kw = extract_row_keywords(concept)
            val1 = get_value(row_kw, year1)
            val2 = get_value(row_kw, year2)
            
            if val1 is not None and val2 is not None:
                return val2 - val1
        
        # "without X segment, what would total Y have been"
        without_match = re.search(r'without\s+(?:the\s+)?(.+?)\s+(?:segment\s+)?(?:in\s+)?(\d{4})\s*,?\s*what\s+would\s+(?:total\s+)?(.+?)\s+have\s+been', q)
        if without_match:
            exclude = without_match.group(1)
            year = int(without_match.group(2))
            total_concept = without_match.group(3)
            
            total_kw = extract_row_keywords(total_concept)
            total_val = get_value(['total'] + total_kw, year)
            
            exclude_kw = extract_row_keywords(exclude)
            exclude_val = get_value(exclude_kw, year)
            
            if total_val is not None and exclude_val is not None:
                return total_val - exclude_val
        
        # Handle "what is the total X from YEAR to YEAR"  or "what is the total X from YEAR-YEAR"
        total_range = re.search(r'(?:total|sum)\s+(?:of\s+)?(.+?)\s+(?:from|for|during|in)\s+(?:the\s+)?(?:years?\s+)?(\d{4})\s*(?:to|-|through|and)\s*(\d{4})', q)
        if total_range:
            concept = total_range.group(1)
            y1 = int(total_range.group(2))
            y2 = int(total_range.group(3))
            
            row_kw = extract_row_keywords(concept)
            values = []
            for y in range(y1, y2 + 1):
                v = get_value(row_kw, y)
                if v is not None:
                    values.append(v)
            if values:
                return sum(values)
        
        # --- Very general fallback ---
        # If we have exactly two values needed and the question asks for a ratio
        
        # Handle "percent increase" for absolute values (losses -> bigger loss = increase)
        if is_pct_change and len(q_years) >= 2:
            year1 = min(q_years)
            year2 = max(q_years)
            
            # Try broader search
            for row in table[1:]:
                label = row[0].lower()
                # Check if multiple question keywords match
                row_kw = extract_row_keywords(q)
                match_count = sum(1 for kw in row_kw if kw in label)
                if match_count >= 2:
                    col1 = find_col_for_year(header, year1)
                    col2 = find_col_for_year(header, year2)
                    if col1 is not None and col2 is not None:
                        v1 = clean_number(row[col1]) if col1 < len(row) else None
                        v2 = clean_number(row[col2]) if col2 < len(row) else None
                        if v1 is not None and v2 is not None and v1 != 0:
                            # For losses (negative numbers), check if question asks about "increase in losses"
                            if ('loss' in q or 'losses' in q) and v1 < 0 and v2 < 0:
                                # Increase in losses means more negative
                                return (abs(v2) - abs(v1)) / abs(v1)
                            return (v2 - v1) / abs(v1)
        
        # Try computing from context numbers
        # "expense of $15 million ... as percentage of ... $37 million"
        if ('percentage' in q or 'percent' in q) and not is_pct_change:
            # Search context for the specific numbers mentioned
            q_kw = extract_row_keywords(q)
            
            # Find relevant sentences
            relevant_nums = []
            for num, sent in context_numbers.items():
                sent_lower = sent.lower()
                match_score = sum(1 for kw in q_kw if kw in sent_lower)
                if match_score > 0:
                    relevant_nums.append((num, match_score, sent))
            
            if len(relevant_nums) >= 2:
                relevant_nums.sort(key=lambda x: -x[1])
                # The larger number is likely the denominator
                nums = [r[0] for r in relevant_nums[:2]]
                if max(nums) != 0:
                    return min(nums) / max(nums)
        
        # Handle simple value lookups
        if simple_value_match and not is_pct_change and not is_portion and not is_average:
            concept = simple_value_match.group(1)
            year = int(simple_value_match.group(2))
            
            row_kw = extract_row_keywords(concept)
            val = get_value(row_kw, year)
            if val is not None:
                return val
        
        # Last resort: try to match numbers from context
        # Handle patterns like "$ X ... $ Y" mentioned in context near question keywords
        
        # For questions about line of credit increase potential
        if 'increase' in q and ('line of credit' in q or 'credit' in q):
            # Look for two dollar amounts in context
            amounts = re.findall(r'\$\s*([\d.]+)\s*billion', full_context.lower())
            if len(amounts) >= 2:
                vals = [float(a) for a in amounts]
                # Find the increase from X to Y
                for i in range(len(vals) - 1):
                    if vals[i+1] > vals[i]:
                        return (vals[i+1] - vals[i]) / vals[i]
        
        # For questions about values from context text (not table)
        # "stock based compensation expense was $37 million" and "$15 million of expense"
        q_kw = extract_row_keywords(q)
        
        # Try to find numbers in context matching question keywords
        context_vals = []
        for sent in re.split(r'[.\n]', full_context):
            sent_lower = sent.lower().strip()
            if not sent_lower:
                continue
            
            kw_match = sum(1 for kw in q_kw if kw in sent_lower)
            if kw_match >= 2:
                amounts = re.findall(r'\$\s*([\d,]+\.?\d*)\s*(million|billion|thousand)?', sent_lower)
                for val_str, unit in amounts:
                    try:
                        v = float(val_str.replace(',', ''))
                        if unit == 'billion':
                            v *= 1000
                        context_vals.append(v)
                    except:
                        pass
        
        # Handle "considering years X-Y, average of Z"
        if is_average and not q_years:
            range_match = re.search(r'(\d{4})\s*[-–]\s*(\d{4})', q)
            if range_match:
                y1 = int(range_match.group(1))
                y2 = int(range_match.group(2))
                
                # Try to find values in context
                vals = []
                for y in range(y1, y2 + 1):
                    # Look in context for values associated with each year
                    for sent in re.split(r'[.\n]', full_context):
                        if str(y) in sent:
                            amounts = re.findall(r'\$\s*([\d,]+\.?\d*)', sent)
                            for a in amounts:
                                try:
                                    vals.append(float(a.replace(',', '')))
                                except:
                                    pass
                
                if vals:
                    return sum(vals) / len(vals)
        
        # --- Handle "what was the average X and Y for Z" ---
        if is_average and 'high' in q and 'low' in q:
            # Find high and low values
            for row in table[1:]:
                if len(row) >= 3:
                    # Check if this row matches the quarter/period
                    period_kw = extract_row_keywords(q)
                    label = row[0].lower()
                    if any(kw in label for kw in period_kw):
                        vals = []
                        for cell in row[1:]:
                            v = clean_number(cell)
                            if v is not None:
                                vals.append(v)
                        if len(vals) >= 2:
                            return sum(vals) / len(vals)
        
        # Try simple two-number operations from context
        if context_vals and len(context_vals) >= 2:
            if 'percentage' in q or 'percent' in q:
                if not is_pct_change:
                    # Smaller / larger
                    return min(context_vals) / max(context_vals)
        
        # Handle "percent increase" with absolute values for losses
        if is_pct_change and len(q_years) >= 2:
            year1 = min(q_years)
            year2 = max(q_years)
            
            # Try every row
            best_row = None
            best_score = 0
            row_kw = extract_row_keywords(q)
            
            for row in table[1:]:
                label = row[0].lower()
                score = sum(1 for kw in row_kw if kw in label)
                if score > best_score:
                    best_score = score
                    best_row = row
            
            if best_row is not None:
                col1 = find_col_for_year(header, year1)
                col2 = find_col_for_year(header, year2)
                if col1 is not None and col2 is not None:
                    v1 = clean_number(best_row[col1]) if col1 < len(best_row) else None
                    v2 = clean_number(best_row[col2]) if col2 < len(best_row) else None
                    if v1 is not None and v2 is not None and v1 != 0:
                        return (v2 - v1) / abs(v1)
        
        # Handle inventory percent increase: (new - old) / old
        if ('percent' in q or 'percentage' in q) and ('increase' in q or 'decrease' in q or 'change' in q):
            if len(q_years) >= 2:
                year1 = min(q_years)
                year2 = max(q_years)
                
                row_kw = extract_row_keywords(q)
                
                # Try each row
                for row in table[1:]:
                    label = row[0].lower()
                    if any(kw in label for kw in row_kw if len(kw) > 3):
                        col1 = find_col_for_year(header, year1)
                        col2 = find_col_for_year(header, year2)
                        
                        if col1 and col2:
                            v1 = clean_number(row[col1]) if col1 < len(row) else None
                            v2 = clean_number(row[col2]) if col2 < len(row) else None
                            
                            if v1 is not None and v2 is not None and v1 != 0:
                                return (v2 - v1) / abs(v1)
        
        # Handle variation/difference between values
        if 'variation' in q or 'difference' in q:
            if 'average' in q and 'highest' in q:
                # Get all values for the row
                row_kw = extract_row_keywords(q)
                vals_dict = get_row_values(row_kw)
                
                numeric_vals = [v for k, v in vals_dict.items() if isinstance(k, int)]
                if not numeric_vals:
                    numeric_vals = list(vals_dict.values())
                
                if numeric_vals:
                    avg = sum(numeric_vals) / len(numeric_vals)
                    highest = max(numeric_vals)
                    return highest - avg
        
        # Handle "number of shares" = amount / price_per_share
        if 'number of shares' in q or 'shares' in q:
            # Look for dividend per share and total amount
            amounts = re.findall(r'\$\s*([\d,]+\.?\d*)\s*(million|billion)?', full_context.lower())
            per_share = re.findall(r'\$\s*([\d.]+)\s+per\s+share', full_context.lower())
            
            # This is too complex for a generic handler
            pass
        
        # Handle questions about values only in context (not in table)
        # E.g., "expense as percentage of compensation"
        # Try to find the two key numbers in context
        if 'percentage' in q or 'percent' in q:
            # Look for dollar amounts in context that match question keywords
            all_amounts = []
            for sent in re.split(r'[.\n]', full_context):
                sent_lower = sent.lower()
                q_kw_local = extract_row_keywords(q)
                relevance = sum(1 for kw in q_kw_local if kw in sent_lower)
                if relevance >= 1:
                    amts = re.findall(r'\$\s*([\d,]+\.?\d*)\s*(million|billion)?', sent_lower)
                    for a, u in amts:
                        try:
                            v = float(a.replace(',', ''))
                            if u == 'billion':
                                v *= 1000
                            all_amounts.append((v, relevance, sent_lower))
                        except:
                            pass
            
            if all_amounts:
                # Sort by relevance
                all_amounts.sort(key=lambda x: -x[1])
        
        # --- Handle: "what is total X from YEAR to YEAR, in millions" ---
        if 'total' in q:
            row_kw = extract_row_keywords(q)
            
            # Check for year range
            range_match = re.search(r'(\d{4})\s*(?:to|-|through|and)\s*(\d{4})', q)
            if range_match:
                y1 = int(range_match.group(1))
                y2 = int(range_match.group(2))
                
                values = []
                for y in range(y1, y2 + 1):
                    v = get_value(row_kw, y)
                    if v is not None:
                        values.append(v)
                
                if values:
                    return sum(values)
        
        return None
    
    def format_output(result):
        """Format the result as expected."""
        if result is None:
            return None
        
        # Round to 5 decimal places to avoid floating point issues
        result = round(result, 5)
        
        # Format as string
        if result == int(result) and abs(result) < 1e10:
            return str(int(result)) + '.0'
        else:
            return str(round(result, 5))
    
    try:
        text = question_text[0] if isinstance(question_text, (list, tuple)) else question_text
        context_before, table, context_after, question = parse_input(text)
        result = solve(context_before, table, context_after, question)
        
        if result is None:
            return None
        
        # Return as a number (float)
        return round(result, 5)
    except Exception as e:
        return None
