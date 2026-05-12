"""Auto-generated code-distilled implementation for extract_reasoning_plan."""

def extract_reasoning_plan(text):
    import re
    import math
    
    # Parse the input text to extract table data, context, and question
    # Extract table
    table_match = re.search(r'## Table\n(.*?)(?=\n## |\n\nReply)', text, re.DOTALL)
    if not table_match:
        return None
    
    table_text = table_match.group(1).strip()
    
    # Parse table into rows
    table_rows = []
    for line in table_text.split('\n'):
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            table_rows.append(cells)
    
    if not table_rows:
        return None
    
    # Extract question
    question_match = re.search(r'## Question\n(.*?)(?=\n\nReply)', text, re.DOTALL)
    if not question_match:
        return None
    question = question_match.group(1).strip().lower()
    
    # Extract context
    context_before = ""
    ctx_match = re.search(r'## Context \(text before table\)\n(.*?)(?=\n## Table)', text, re.DOTALL)
    if ctx_match:
        context_before = ctx_match.group(1).strip().lower()
    
    context_after = ""
    ctx_after_match = re.search(r'## Context \(text after table\)\n(.*?)(?=\n## Question)', text, re.DOTALL)
    if ctx_after_match:
        context_after = ctx_after_match.group(1).strip().lower()
    
    full_context = context_before + " " + context_after
    
    def parse_number(s):
        """Parse a number from a string, handling currency symbols, parentheses for negatives, percentages."""
        if s is None:
            return None
        s = s.strip()
        # Remove common prefixes/suffixes
        s = re.sub(r'[,]', '', s)
        # Check for parenthetical negatives like -57 ( 57 ) or (57)
        paren_match = re.match(r'^-?\s*\$?\s*([\d.]+)\s*\(\s*[\d.]+\s*\)$', s)
        if paren_match:
            return -float(paren_match.group(1))
        # Check for pattern like "( $ 4 )" or "( $4 )"
        paren_match2 = re.match(r'^\(\s*\$?\s*([\d.]+)\s*\)$', s)
        if paren_match2:
            return -float(paren_match2.group(1))
        # Check for pattern like "$ -181 ( 181 )"
        neg_paren = re.match(r'^\$?\s*-\s*([\d.]+)\s*\(\s*[\d.]+\s*\)$', s)
        if neg_paren:
            return -float(neg_paren.group(1))
        
        # Remove $ signs
        s = s.replace('$', '').strip()
        
        # Handle negative in parentheses
        if s.startswith('(') and s.endswith(')'):
            s = s[1:-1].strip()
            try:
                return -float(s)
            except:
                return None
        
        # Remove percentage signs for detection but note it
        s_no_pct = s.replace('%', '').strip()
        # Remove trailing text like "( 4.8 % )" patterns
        s_no_pct = re.sub(r'\(.*?\)', '', s_no_pct).strip()
        
        # Try to parse
        try:
            return float(s_no_pct)
        except:
            return None
    
    def find_value_in_table(row_key, col_key=None):
        """Find a value in the table by row and column keywords."""
        if not table_rows or len(table_rows) < 2:
            return None
        
        header = table_rows[0]
        
        # Try to find the row
        for row in table_rows[1:]:
            if not row:
                continue
            row_label = row[0].lower().strip()
            if row_key.lower() in row_label or row_label in row_key.lower():
                if col_key is not None:
                    # Find column
                    for ci, h in enumerate(header):
                        if col_key.lower() in h.lower() or h.lower() in col_key.lower():
                            if ci < len(row):
                                return parse_number(row[ci])
                    # Try matching column by value
                    for ci in range(1, len(row)):
                        if col_key.lower() in header[ci].lower():
                            return parse_number(row[ci])
                elif len(row) >= 2:
                    return parse_number(row[1])
        return None
    
    def get_table_as_dict():
        """Convert table to a more usable format."""
        if not table_rows or len(table_rows) < 2:
            return [], []
        header = [h.strip().lower() for h in table_rows[0]]
        data = []
        for row in table_rows[1:]:
            if len(row) >= len(header):
                row_dict = {}
                for i, h in enumerate(header):
                    row_dict[h] = row[i].strip() if i < len(row) else ''
                data.append(row_dict)
            elif len(row) >= 2:
                row_dict = {}
                for i in range(len(row)):
                    if i < len(header):
                        row_dict[header[i]] = row[i].strip()
                data.append(row_dict)
        return header, data
    
    def find_cell(row_keyword, col_keyword):
        """More flexible cell finder."""
        header, data = get_table_as_dict()
        if not data:
            return None
        
        row_keyword = row_keyword.lower().strip()
        col_keyword = col_keyword.lower().strip()
        
        for row_dict in data:
            first_key = header[0] if header else ''
            row_label = row_dict.get(first_key, '').lower()
            
            # Check if row matches
            row_match = False
            if row_keyword in row_label or row_label in row_keyword:
                row_match = True
            # Also check if any cell in first column matches
            for key in row_dict:
                if row_keyword in row_dict[key].lower():
                    row_match = True
                    break
            
            if row_match:
                # Find matching column
                for h in header[1:]:
                    if col_keyword in h or h in col_keyword:
                        val = parse_number(row_dict.get(h, ''))
                        if val is not None:
                            return val
                # Try partial matching
                for h in header[1:]:
                    if any(w in h for w in col_keyword.split()):
                        val = parse_number(row_dict.get(h, ''))
                        if val is not None:
                            return val
        return None
    
    def get_all_values_for_row(row_keyword):
        """Get all numeric values for a matching row."""
        header, data = get_table_as_dict()
        if not data:
            return {}
        
        row_keyword = row_keyword.lower().strip()
        
        for row_dict in data:
            first_key = header[0] if header else ''
            row_label = row_dict.get(first_key, '').lower()
            
            if row_keyword in row_label or row_label in row_keyword:
                result = {}
                for h in header[1:]:
                    val = parse_number(row_dict.get(h, ''))
                    if val is not None:
                        result[h] = val
                return result
        return {}
    
    def get_column_values(col_keyword):
        """Get all values in a column."""
        header, data = get_table_as_dict()
        if not data:
            return {}
        
        col_keyword = col_keyword.lower().strip()
        target_col = None
        for h in header:
            if col_keyword in h or h in col_keyword:
                target_col = h
                break
        
        if target_col is None:
            for h in header:
                if any(w in h for w in col_keyword.split()):
                    target_col = h
                    break
        
        if target_col is None:
            return {}
        
        result = {}
        first_key = header[0]
        for row_dict in data:
            row_label = row_dict.get(first_key, '').lower()
            val = parse_number(row_dict.get(target_col, ''))
            if val is not None:
                result[row_label] = val
        return result
    
    # Build a simple representation of the table
    header, data = get_table_as_dict()
    
    # Helper to find two year values for percent change questions
    def extract_years_from_question(q):
        """Extract year references from question."""
        year_pattern = r'((?:19|20)\d{2})'
        years = re.findall(year_pattern, q)
        return years
    
    def find_value_by_year_and_label(year, label):
        """Find a value given a year and a row label."""
        # Try to find year in column headers and label in row labels
        val = find_cell(label, year)
        if val is not None:
            return val
        # Try year in row labels and label in column headers
        val = find_cell(year, label)
        if val is not None:
            return val
        return None
    
    def simple_two_col_table():
        """Check if table is a simple two-column table (label | value)."""
        if not header or len(header) < 2:
            return False
        return len(header) == 2
    
    def get_simple_value(row_keyword):
        """Get value from a simple two-column table."""
        if not simple_two_col_table():
            return None
        for row_dict in data:
            first_key = header[0]
            row_label = row_dict.get(first_key, '').lower()
            if row_keyword.lower() in row_label:
                second_key = header[1]
                return parse_number(row_dict.get(second_key, ''))
        return None
    
    # Now try to answer the question
    years = extract_years_from_question(question)
    
    # Detect question type
    q = question.lower()
    
    # Helper function to format output
    def format_percent(value, with_sign=True):
        """Format a percentage value."""
        # Round to 2 decimal places
        rounded = round(value * 100, 2)
        if rounded == int(rounded):
            return f"{int(rounded)}%"
        # Remove trailing zeros but keep at least one decimal
        s = f"{rounded:.2f}".rstrip('0').rstrip('.')
        return f"{s}%"
    
    def format_number(value):
        """Format a number appropriately."""
        if value == int(value):
            return str(int(value))
        return str(value)
    
    # Try to detect and answer various question types
    
    # PERCENT CHANGE / PERCENTAGE CHANGE questions
    is_pct_change = any(phrase in q for phrase in [
        'percent change', 'percentage change', 'percent increase', 'percentage increase',
        'percent decrease', 'percentage decrease', 'percentual increase', 'percentual decrease',
        'growth rate', 'roi of an investment', 'what is the roi',
        'percent did', 'percentage cumulative', 'cumulative total shareholder return',
        'five year change', 'total five year change',
        'what was the percentage cumulative return',
        'percent increase', 'percent did inventories receive',
    ])
    
    is_ratio = 'ratio' in q and 'percent' not in q
    is_average = 'average' in q and 'percent' not in q and 'change' not in q
    is_portion = any(phrase in q for phrase in ['what portion', 'what percentage of', 'what percent of', 'what was the percent of'])
    is_difference = any(phrase in q for phrase in ['change in', 'net change', 'difference'])
    is_total = 'total' in q and ('sum' in q or 'what is the total' in q or 'what was the total' in q)
    is_lowest = 'lowest' in q or ('minimum' in q and 'total' not in q)
    is_greatest = 'greatest' in q or 'highest' in q or 'maximum' in q
    
    # Handle specific question patterns
    
    # --- PERCENT CHANGE between two periods ---
    if is_pct_change and len(years) >= 2 and not is_portion:
        year1, year2 = years[0], years[1]
        # Determine what metric to look for
        # Try to identify the row/metric from the question
        
        # Common patterns: "percent change in X from YEAR1 to YEAR2"
        # or "percentage increase in X from YEAR1 to YEAR2"
        
        # Extract the metric name
        metric_patterns = [
            r'(?:percent(?:age)?|percentual)\s+(?:change|increase|decrease)\s+in\s+(.*?)\s+(?:from|between)',
            r'(?:percent(?:age)?)\s+(?:change|increase|decrease)\s+(?:of|in)\s+(.*?)\s+(?:from|between)',
            r'growth\s+rate\s+(?:of|in)\s+(.*?)\s+(?:from|between)',
            r'(?:percent(?:age)?)\s+(?:cumulative\s+)?(?:return|change)\s+(?:for|of|in)\s+(.*?)\s+(?:for|from|between)',
        ]
        
        metric = None
        for pat in metric_patterns:
            m = re.search(pat, q)
            if m:
                metric = m.group(1).strip()
                break
        
        # Also try: "what was the percentage change in X from..."
        if metric is None:
            m = re.search(r'(?:what\s+(?:was|is)\s+the\s+)?(?:percent(?:age)?)\s+(?:change|increase|decrease|growth)\s+(?:in|of)\s+(.*?)\s+(?:from|between|during)', q)
            if m:
                metric = m.group(1).strip()
        
        if metric is None:
            # Try "what percent did X receive between"
            m = re.search(r'percent\s+(?:did|does)\s+(.*?)\s+(?:receive|increase|decrease|change)', q)
            if m:
                metric = m.group(1).strip()
        
        if metric is None:
            # Try "growth rate of X from"  
            m = re.search(r'growth\s+rate\s+of\s+(.*?)\s+from', q)
            if m:
                metric = m.group(1).strip()
        
        # For ROI questions
        if 'roi' in q:
            m = re.search(r'(?:roi\s+of\s+an?\s+investment\s+in)\s+(.*?)\s+from', q)
            if m:
                metric = m.group(1).strip()
        
        val1 = None
        val2 = None
        
        if metric:
            # Clean metric
            metric_clean = metric.replace("'s", '').replace("2019s", '').strip()
            
            # Try direct lookup
            val1 = find_cell(metric_clean, year1)
            val2 = find_cell(metric_clean, year2)
            
            # If not found, try partial matching
            if val1 is None or val2 is None:
                for row_dict in data:
                    first_key = header[0]
                    row_label = row_dict.get(first_key, '').lower()
                    
                    # Check various matching strategies
                    metric_words = [w for w in metric_clean.lower().split() if len(w) > 2]
                    match_count = sum(1 for w in metric_words if w in row_label)
                    
                    if match_count >= max(1, len(metric_words) * 0.5):
                        for h in header[1:]:
                            if year1 in h:
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None:
                                    val1 = v
                            if year2 in h:
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None:
                                    val2 = v
        
        # If still not found, try using years as row keys
        if val1 is None or val2 is None:
            # Check if years are in row labels (simple two-column or multi-column table)
            for row_dict in data:
                first_key = header[0]
                row_label = row_dict.get(first_key, '').lower()
                if year1 in row_label:
                    for h in header[1:]:
                        v = parse_number(row_dict.get(h, ''))
                        if v is not None:
                            val1 = v
                            break
                if year2 in row_label:
                    for h in header[1:]:
                        v = parse_number(row_dict.get(h, ''))
                        if v is not None:
                            val2 = v
                            break
        
        # For cumulative return questions (like "percentage cumulative return for X for five years ended Y")
        if 'cumulative' in q and val1 is not None and val2 is None:
            # Usually comparing to the base $100
            if val1 is not None:
                result = val1 - 100
                return f"{result}%"
        
        if val1 is not None and val2 is not None and val1 != 0:
            pct_change = (val2 - val1) / abs(val1)
            
            # Determine output format based on expected patterns
            # Check if question asks for "percent" explicitly with % sign expected
            if 'roi' in q:
                # ROI typically returned as decimal
                return f"{round(pct_change, 4)}"
            
            # Format as percentage
            result_pct = pct_change * 100
            result_pct_rounded = round(result_pct, 2)
            
            # Check if it's a clean percentage
            if result_pct_rounded == int(result_pct_rounded):
                return f"{int(result_pct_rounded)}%"
            else:
                s = f"{result_pct_rounded:.2f}"
                # Don't strip trailing zeros for consistency
                return f"{s}%"
    
    # Handle "cumulative total shareholder return" or "percentage cumulative return"  
    if ('cumulative' in q and 'return' in q) or ('five year change' in q) or ('total five year change' in q):
        if len(years) >= 1:
            target_year = years[-1]
            # Find the row that matches the entity mentioned
            metric = None
            # Try to extract entity
            m = re.search(r'(?:for|of|in)\s+(.*?)(?:\s+for|\s+from|\s+since|\?)', q)
            if m:
                metric = m.group(1).strip()
            
            if metric:
                val = find_cell(metric, target_year)
                if val is not None:
                    # Cumulative return from $100 base
                    result = val - 100
                    return f"{result}%"
            
            # Try "total five year change in the X"
            if 'total five year change' in q or 'total change' in q:
                m = re.search(r'(?:change\s+in\s+(?:the\s+)?)(.*?)(?:\?|$)', q)
                if m:
                    metric = m.group(1).strip()
                    # Find start and end values
                    vals = get_all_values_for_row(metric)
                    if vals:
                        sorted_vals = sorted(vals.items())
                        if len(sorted_vals) >= 2:
                            start_val = sorted_vals[0][1]
                            end_val = sorted_vals[-1][1]
                            return format_number(end_val - start_val)
    
    # --- PORTION / PERCENTAGE OF questions ---
    if is_portion or ('as a percentage of' in q) or ('what percent of' in q) or ('what was the percent of' in q):
        # Pattern: "what portion of X is Y" or "what percentage of X is Y"
        # Or: "X as a percentage of Y"
        
        numerator_val = None
        denominator_val = None
        
        # Try various patterns
        patterns = [
            r'(?:what\s+(?:portion|percentage|percent)\s+of\s+(?:the\s+)?)(.*?)\s+(?:is|are|was|were)\s+(?:related\s+to|dedicated\s+to|due\s+to|comprised\s+of|attributable\s+to|associated\s+with|incurred\s+from)\s+(.*?)(?:\?|$)',
            r'(?:what\s+(?:portion|percentage|percent)\s+of\s+(?:the\s+)?)(.*?)\s+(?:is|are|was|were)\s+(.*?)(?:\?|$)',
            r'(.*?)\s+as\s+a\s+percentage\s+of\s+(.*?)(?:\?|$)',
            r'(?:what\s+(?:portion|percentage|percent)\s+of\s+)(.*?)\s+(?:is|was)\s+(?:related\s+to\s+|due\s+(?:to|in)\s+|comprised\s+of\s+|associated\s+with\s+)(.*?)(?:\?|$)',
            r'what\s+(?:was|is)\s+the\s+percent\s+of\s+the\s+(.*?)\s+that\s+was\s+(?:associated\s+with|due\s+(?:in|to))\s+(.*?)(?:\?|$)',
        ]
        
        total_key = None
        part_key = None
        
        for pat in patterns:
            m = re.search(pat, q)
            if m:
                total_key = m.group(1).strip()
                part_key = m.group(2).strip()
                break
        
        # Special case: "what was the percent of the total ... that was associated with ..."
        if total_key is None:
            m = re.search(r'percent\s+of\s+(?:the\s+)?total\s+(.*?)\s+(?:that\s+)?(?:was|is)\s+(?:associated\s+with|due\s+(?:in|to))\s+(.*?)(?:\?|$)', q)
            if m:
                total_key = 'total ' + m.group(1).strip()
                part_key = m.group(2).strip()
        
        # "what percent of total ... due in YEAR" pattern
        if total_key is None:
            m = re.search(r'(?:what\s+(?:was|is)\s+the\s+)?percent(?:age)?\s+of\s+(?:the\s+)?(?:total\s+)?(.*?)\s+(?:that\s+(?:was|is)\s+)?(?:due|payable)\s+in\s+(\d{4})', q)
            if m:
                total_key = 'total'
                part_key = m.group(2).strip()
        
        if total_key and part_key:
            year_ctx = None
            if years:
                year_ctx = years[-1]
            
            # Try to find values
            # First, find the total/denominator
            for row_dict in data:
                first_key_h = header[0]
                row_label = row_dict.get(first_key_h, '').lower()
                
                total_words = [w for w in total_key.lower().split() if len(w) > 2]
                part_words = [w for w in part_key.lower().split() if len(w) > 2]
                
                # Match total
                total_match = sum(1 for w in total_words if w in row_label)
                if total_match >= max(1, len(total_words) * 0.4) or 'total' in row_label:
                    if 'total' in row_label or total_match >= len(total_words) * 0.5:
                        if year_ctx:
                            for h in header[1:]:
                                if year_ctx in h:
                                    v = parse_number(row_dict.get(h, ''))
                                    if v is not None:
                                        denominator_val = v
                        elif len(header) == 2:
                            v = parse_number(row_dict.get(header[1], ''))
                            if v is not None:
                                denominator_val = v
                
                # Match part
                part_match = sum(1 for w in part_words if w in row_label)
                if part_match >= max(1, len(part_words) * 0.4):
                    if year_ctx:
                        for h in header[1:]:
                            if year_ctx in h:
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None:
                                    numerator_val = v
                    elif len(header) == 2:
                        v = parse_number(row_dict.get(header[1], ''))
                        if v is not None:
                            numerator_val = v
            
            # For "payments as a percentage of" type questions
            if 'as a percentage of' in q:
                # Swap: numerator is the first mentioned, denominator is second
                m = re.search(r'(.*?)\s+as\s+a\s+percentage\s+of\s+(.*?)(?:\?|$)', q)
                if m:
                    num_key = m.group(1).strip()
                    den_key = m.group(2).strip()
                    
                    for row_dict in data:
                        first_key_h = header[0]
                        row_label = row_dict.get(first_key_h, '').lower()
                        
                        if any(w in row_label for w in num_key.lower().split() if len(w) > 3):
                            if len(header) == 2:
                                v = parse_number(row_dict.get(header[1], ''))
                                if v is not None:
                                    numerator_val = v
                        
                        if any(w in row_label for w in den_key.lower().split() if len(w) > 3):
                            if len(header) == 2:
                                v = parse_number(row_dict.get(header[1], ''))
                                if v is not None:
                                    denominator_val = v
            
            if numerator_val is not None and denominator_val is not None and denominator_val != 0:
                ratio = numerator_val / denominator_val
                # Return as decimal or percentage based on context
                result = round(ratio, 4)
                if abs(result) < 0.01:
                    return str(round(ratio, 6))
                return str(result)
    
    # --- AVERAGE questions ---
    if is_average:
        if len(years) >= 2:
            # Average of values across years
            year_vals = []
            
            # Try to find what metric to average
            m = re.search(r'average\s+(.*?)(?:\s+(?:from|for|in|between|during))', q)
            if not m:
                m = re.search(r'average\s+(.*?)(?:\?|$)', q)
            
            metric = m.group(1).strip() if m else None
            
            if metric:
                for y in years:
                    val = find_cell(metric, y)
                    if val is not None:
                        year_vals.append(val)
                
                # Also try with years as column headers
                if not year_vals:
                    for row_dict in data:
                        first_key_h = header[0]
                        row_label = row_dict.get(first_key_h, '').lower()
                        metric_words = [w for w in metric.lower().split() if len(w) > 2]
                        if any(w in row_label for w in metric_words):
                            for h in header[1:]:
                                for y in years:
                                    if y in h:
                                        v = parse_number(row_dict.get(h, ''))
                                        if v is not None:
                                            year_vals.append(v)
            
            if year_vals:
                avg = sum(year_vals) / len(year_vals)
                if avg == int(avg):
                    return str(int(avg))
                return str(round(avg, 1))
        
        # Average of high and low in same row
        if 'high and low' in q or ('high' in q and 'low' in q):
            high_val = None
            low_val = None
            
            # Find the relevant row
            target_year = years[0] if years else None
            
            for row_dict in data:
                first_key_h = header[0]
                row_label = row_dict.get(first_key_h, '').lower()
                
                # Check if this row matches the period mentioned
                period_match = False
                if target_year and target_year in row_label:
                    period_match = True
                if 'second quarter' in q and 'second' in row_label:
                    period_match = True
                if 'first quarter' in q and 'first' in row_label:
                    period_match = True
                if 'third quarter' in q and 'third' in row_label:
                    period_match = True
                if 'fourth quarter' in q and 'fourth' in row_label:
                    period_match = True
                
                if period_match:
                    for h in header[1:]:
                        if 'high' in h.lower():
                            high_val = parse_number(row_dict.get(h, ''))
                        if 'low' in h.lower():
                            low_val = parse_number(row_dict.get(h, ''))
                    
                    if high_val is not None and low_val is not None:
                        avg = (high_val + low_val) / 2
                        return str(round(avg, 2))
    
    # --- Average price (high + low) / 2 ---  
    if 'average price' in q or ('average' in q and ('high' in q or 'low' in q or 'price' in q)):
        for row_dict in data:
            first_key_h = header[0]
            row_label = row_dict.get(first_key_h, '').lower()
            
            period_match = False
            if 'third quarter' in q and ('third' in row_label or 'q3' in row_label or 'september' in row_label):
                period_match = True
            if 'second quarter' in q and ('second' in row_label or 'q2' in row_label or 'june' in row_label):
                period_match = True
            if 'first quarter' in q and ('first' in row_label or 'q1' in row_label or 'march' in row_label):
                period_match = True
            if 'fourth quarter' in q and ('fourth' in row_label or 'q4' in row_label or 'december' in row_label):
                period_match = True
            
            if years:
                if years[0] in row_label:
                    period_match = True
            
            if period_match:
                high_val = None
                low_val = None
                for h in header[1:]:
                    if 'high' in h.lower():
                        v = parse_number(row_dict.get(h, ''))
                        if v is not None:
                            high_val = v
                    if 'low' in h.lower():
                        v = parse_number(row_dict.get(h, ''))
                        if v is not None:
                            low_val = v
                
                if high_val is not None and low_val is not None:
                    avg = (high_val + low_val) / 2
                    return str(round(avg, 1))
    
    # --- DIFFERENCE / CHANGE IN questions ---
    if is_difference and not is_pct_change and len(years) >= 2:
        year1, year2 = years[0], years[1]
        
        # Extract metric
        m = re.search(r'(?:change|difference)\s+in\s+(.*?)\s+(?:from|between)', q)
        if not m:
            m = re.search(r'(?:net\s+change\s+in\s+(?:the\s+)?(?:number\s+of\s+)?)(.*?)\s+(?:from|between)', q)
        
        metric = m.group(1).strip() if m else None
        
        val1 = None
        val2 = None
        
        if metric:
            # For "net change in number of X from YEAR1 to YEAR2"
            # We need ending balance for each year
            
            # Try to find "open sites ending balance" or similar
            for row_dict in data:
                first_key_h = header[0]
                row_label = row_dict.get(first_key_h, '').lower()
                
                # Look for ending balance row or the metric itself
                if 'ending' in row_label or 'balance' in row_label or metric.lower() in row_label:
                    for h in header[1:]:
                        if year1 in h:
                            v = parse_number(row_dict.get(h, ''))
                            if v is not None:
                                val1 = v
                        if year2 in h:
                            v = parse_number(row_dict.get(h, ''))
                            if v is not None:
                                val2 = v
            
            # If ending balance not found, try the metric directly  
            if val1 is None or val2 is None:
                for row_dict in data:
                    first_key_h = header[0]
                    row_label = row_dict.get(first_key_h, '').lower()
                    metric_words = [w for w in metric.lower().split() if len(w) > 2]
                    if any(w in row_label for w in metric_words):
                        for h in header[1:]:
                            if year1 in h:
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None and val1 is None:
                                    val1 = v
                            if year2 in h:
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None and val2 is None:
                                    val2 = v
        
        if val1 is not None and val2 is not None:
            diff = val2 - val1
            if diff == int(diff):
                return str(int(diff))
            return str(diff)
    
    # --- TOTAL / SUM questions ---
    if 'total' in q and ('what is the total' in q or 'what was the total' in q):
        # Sum specific values
        vals = []
        
        # Check for "total net pension cost from 2016-2018"
        m = re.search(r'total\s+(.*?)\s+(?:from|for|between|in)\s+(\d{4})\s*(?:-|to|and)\s*(\d{4})', q)
        if m:
            metric = m.group(1).strip()
            y_start = m.group(2)
            y_end = m.group(3)
            
            for row_dict in data:
                first_key_h = header[0]
                row_label = row_dict.get(first_key_h, '').lower()
                metric_words = [w for w in metric.lower().split() if len(w) > 2]
                if any(w in row_label for w in metric_words):
                    for h in header[1:]:
                        for y in range(int(y_start), int(y_end) + 1):
                            if str(y) in h:
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None:
                                    vals.append(v)
            
            if vals:
                total = sum(vals)
                if total == int(total):
                    return str(int(total))
                return str(total)
    
    # --- LOWEST / MINIMUM questions ---
    if is_lowest:
        # Find the row mentioned and get the minimum value
        # "what is the lowest segment operating income"
        m = re.search(r'lowest\s+(.*?)(?:\?|$)', q)
        if not m:
            m = re.search(r'minimum\s+(.*?)(?:\?|$)', q)
        
        if m:
            metric = m.group(1).strip()
            min_val = None
            
            for row_dict in data:
                first_key_h = header[0]
                row_label = row_dict.get(first_key_h, '').lower()
                metric_words = [w for w in metric.lower().split() if len(w) > 2]
                if any(w in row_label for w in metric_words) or sum(1 for w in metric_words if w in row_label) >= len(metric_words) * 0.4:
                    for h in header[1:]:
                        v = parse_number(row_dict.get(h, ''))
                        if v is not None:
                            if min_val is None or v < min_val:
                                min_val = v
            
            if min_val is not None:
                if min_val == int(min_val):
                    return str(int(min_val))
                return str(min_val)
    
    # --- GREATEST / MAXIMUM questions ---
    if is_greatest:
        m = re.search(r'(?:greatest|highest|maximum)\s+(.*?)(?:\s+(?:for|in|during))?\s*(?:\?|$)', q)
        if m:
            metric = m.group(1).strip()
            max_val = None
            
            for row_dict in data:
                first_key_h = header[0]
                row_label = row_dict.get(first_key_h, '').lower()
                metric_words = [w for w in metric.lower().split() if len(w) > 2]
                if any(w in row_label for w in metric_words):
                    for h in header[1:]:
                        v = parse_number(row_dict.get(h, ''))
                        if v is not None:
                            if max_val is None or v > max_val:
                                max_val = v
            
            if max_val is not None:
                if max_val == int(max_val):
                    return str(int(max_val))
                return str(max_val)
    
    # --- RATIO questions ---
    if is_ratio and len(years) >= 1:
        # "ratio of X to Y"
        m = re.search(r'ratio\s+of\s+(?:the\s+)?(.*?)\s+(?:to|and)\s+(.*?)(?:\?|$)', q)
        if m:
            num_key = m.group(1).strip()
            den_key = m.group(2).strip()
            
            year = years[0] if years else None
            
            num_val = None
            den_val = None
            
            for row_dict in data:
                first_key_h = header[0]
                row_label = row_dict.get(first_key_h, '').lower()
                
                if any(w in row_label for w in num_key.lower().split() if len(w) > 2):
                    if year:
                        for h in header[1:]:
                            if year in h:
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None:
                                    num_val = v
                    elif len(header) == 2:
                        v = parse_number(row_dict.get(header[1], ''))
                        if v is not None:
                            num_val = v
                
                if any(w in row_label for w in den_key.lower().split() if len(w) > 2):
                    if year:
                        for h in header[1:]:
                            if year in h:
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None:
                                    den_val = v
                    elif len(header) == 2:
                        v = parse_number(row_dict.get(header[1], ''))
                        if v is not None:
                            den_val = v
            
            if num_val is not None and den_val is not None and den_val != 0:
                ratio = num_val / den_val
                return str(round(ratio, 3))
    
    # --- Specific value lookup questions ---
    # "what was X in YEAR" or "how much was X"
    
    # --- Handle questions about values from context (not just table) ---
    
    # Try to handle various specific question patterns
    
    # "how many shares" / "what was the number of shares"
    if 'number of shares' in q or 'how many' in q:
        # Look for division: amount / per_share = shares
        # e.g., $55 million / $0.40 per share
        
        # Check context for relevant numbers
        pass
    
    # "what is the total value of X" - multiplication
    if 'total value' in q:
        # e.g., "total value of fixed maturities and cash" = total * percentage
        pass
    
    # --- Generic value lookup ---
    # For questions that just ask for a specific value
    
    # Try to extract what's being asked
    # "what was the average net revenue from 2010 to 2011"
    if 'average' in q and 'net revenue' in q:
        vals = []
        for row_dict in data:
            first_key_h = header[0]
            row_label = row_dict.get(first_key_h, '').lower()
            if 'net revenue' in row_label or 'revenue' in row_label:
                for h in header[1:]:
                    for y in years:
                        if y in h:
                            v = parse_number(row_dict.get(h, ''))
                            if v is not None:
                                vals.append(v)
        
        if not vals and len(years) >= 2:
            # Try years as row labels
            for y in years:
                for row_dict in data:
                    first_key_h = header[0]
                    row_label = row_dict.get(first_key_h, '').lower()
                    if y in row_label:
                        for h in header[1:]:
                            if 'net revenue' in h.lower() or 'revenue' in h.lower():
                                v = parse_number(row_dict.get(h, ''))
                                if v is not None:
                                    vals.append(v)
        
        # Also check if years are in row labels in a two-column table
        if not vals:
            for y in years:
                for row_dict in data:
                    first_key_h = header[0]
                    row_label = row_dict.get(first_key_h, '').lower()
                    if y in row_label and 'net revenue' in row_label:
                        v = parse_number(row_dict.get(header[1], ''))
                        if v is not None:
                            vals.append(v)
        
        if vals:
            avg = sum(vals) / len(vals)
            return str(round(avg, 1))
    
    # --- Fallback: Try to handle the question more generically ---
    
    # For percentage-of-total questions with year in column
    if ('percent' in q or 'portion' in q) and not is_pct_change:
        # Try to identify numerator and denominator from table
        pass
    
    # For simple arithmetic from context
    # "what were capital expenditures ... exclusive of the amount incurred during 2003"
    if 'exclusive' in q or 'excluding' in q:
        pass
    
    # Generic: try to find the answer based on keywords in the question
    # Look for numbers in context that answer the question
    
    return None
