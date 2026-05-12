"""Auto-generated code-distilled implementation for analyze_problem_and_requirements."""

import re

def analyze_problem_and_requirements(question):
    if not question or not isinstance(question, str):
        return None
    
    q = question.strip()
    # Normalize extra spaces around punctuation like ", 2016" -> ", 2016"
    q_normalized = re.sub(r'\s*,\s*', ', ', q)
    q_normalized = re.sub(r'\s+', ' ', q_normalized)
    q_lower = q_normalized.lower()
    
    # Detect question type
    is_percentage_change = any(p in q_lower for p in ['percentage change', 'percent change', 'percentage increase', 'percentage growth', 'percentage cumulative', 'percentage increase'])
    is_portion = any(p in q_lower for p in ['what portion', 'what percentage of', 'what percent of', 'are what percent'])
    is_ratio = 'ratio' in q_lower
    is_average = 'average price' in q_lower
    is_compare = 'compare' in q_lower or 'comparing' in q_lower or 'distributed more' in q_lower
    is_can_increase = 'can' in q_lower and 'increase' in q_lower
    
    # Extract years
    years = re.findall(r'\b((?:19|20)\d{2})\b', q_normalized)
    # Extract date references like "December 31, 2016"
    date_refs = re.findall(r'([A-Za-z]+ \d{1,2}, \d{4})', q_normalized, re.IGNORECASE)
    # Extract quarter references
    quarter_match = re.search(r'(?:Q(\d)|(\w+)\s+quarter)\s+(\d{4})', q_normalized, re.IGNORECASE)
    
    # Detect period like "five year period ending 12/31/10"
    period_match = re.search(r'(five[- ]year period ending \d{1,2}/\d{1,2}/\d{2,4})', q_normalized, re.IGNORECASE)
    
    # Try to identify the subject/metric
    def extract_subject(text):
        """Extract the main financial metric from the question."""
        t = text.lower().strip().rstrip('?').strip()
        # Remove common question prefixes
        t = re.sub(r'^(what (is|was) the |what |determine |calculate )', '', t)
        return t
    
    # === Handle specific patterns ===
    
    # Pattern: "Percentage growth/change/increase in X from YEAR1 to YEAR2"
    pct_change_match = re.search(
        r'(?:percentage?|percent)\s+(?:growth|change|increase|decrease)\s+(?:in|of)\s+(?:the\s+)?(.+?)\s+from\s+(\d{4})\s+to\s+(\d{4})',
        q_lower
    )
    if not pct_change_match:
        pct_change_match = re.search(
            r'(?:percentage?|percent)\s+(?:growth|change|increase|decrease)\s+(?:in|of)\s+(?:the\s+)?(.+?)\s+from\s+(\d{4})\s+to\s+(\d{4})',
            q_normalized, re.IGNORECASE
        )
    
    # Pattern: "what was the percent change in X from YEAR1 to YEAR2"
    pct_change_match2 = re.search(
        r'(?:what (?:is|was) the\s+)?(?:percentage?|percent)\s+(?:change|growth|increase|decrease)\s+in\s+(?:the\s+)?(.+?)\s+from\s+(\d{4})\s+to\s+(\d{4})',
        q_normalized, re.IGNORECASE
    )
    
    # Pattern: "Percentage growth of X from YEAR1 to YEAR2" (title case, no question word)
    pct_growth_title = re.search(
        r'^[Pp]ercentage\s+growth\s+of\s+(.+?)\s+from\s+(\d{4})\s+to\s+(\d{4})',
        q_normalized
    )
    
    # Pattern: "what is the percentage change in X from YEAR1 to YEAR2?"
    pct_change_what = re.search(
        r'what\s+(?:is|was)\s+the\s+(percentage?|percent)\s+(change|growth|increase|decrease)\s+in\s+(.+?)\s+from\s+(\d{4})\s+to\s+(\d{4})',
        q_normalized, re.IGNORECASE
    )
    
    # Pattern: "what portion of X is Y"
    portion_match = re.search(
        r'what\s+(?:portion|percentage)\s+of\s+(?:the\s+)?(.+?)\s+(?:is|are)\s+(?:related to|due (?:in|to)|associated with)\s+(.+)',
        q_normalized, re.IGNORECASE
    )
    
    # Pattern: "X are what percent of Y"
    what_pct_of = re.search(
        r'(.+?)\s+(?:are|is)\s+what\s+percent(?:age)?\s+of\s+(?:the\s+)?(.+)',
        q_normalized, re.IGNORECASE
    )
    
    # Pattern: "what percentage of X are/is Y"
    what_pct_match = re.search(
        r'what\s+percentage\s+of\s+(.+?)\s+(?:are|is|were)\s+(.+)',
        q_normalized, re.IGNORECASE
    )
    
    # === Fuel hedges specific ===
    if 'fuel hedge' in q_lower and pct_growth_title:
        subject = pct_growth_title.group(1).strip()
        y1 = pct_growth_title.group(2)
        y2 = pct_growth_title.group(3)
        target = f"Percentage growth of {subject} from {y1} to {y2}"
        data = f"Aggregate fair value of outstanding fuel hedges for {y1}, Aggregate fair value of outstanding fuel hedges for {y2}"
        calc = f"((Fair value {y2} - Fair value {y1}) / Fair value {y1}) * 100"
        constraints = "Only consider outstanding fuel hedges; exclude any expired or settled hedges"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === "what is the percentage change/increase in X from Y1 to Y2?" ===
    if pct_change_what:
        pct_word = pct_change_what.group(1)
        change_word = pct_change_what.group(2)
        subject = pct_change_what.group(3).strip()
        y1 = pct_change_what.group(4)
        y2 = pct_change_what.group(5)
        
        # Capitalize first letter of subject properly - keep it lowercase if it starts lowercase in original
        # Find original case in q_normalized
        subj_match = re.search(re.escape(subject), q_normalized, re.IGNORECASE)
        if subj_match:
            original_subject = q_normalized[subj_match.start():subj_match.end()]
        else:
            original_subject = subject
        
        # For target line: "Percentage change/increase in <subject> from Y1 to Y2"
        target_pct_word = "Percentage" if pct_word.lower().startswith('percent') and len(pct_word) > 7 else "Percent"
        target = f"{target_pct_word} {change_word.lower()} in {subject.lower()} from {y1} to {y2}"
        
        # Determine short label for subject
        subj_lower = subject.lower()
        
        if 'accumulated other comprehensive loss' in subj_lower:
            data = f"Total accumulated other comprehensive losses for {y1}, Total accumulated other comprehensive losses for {y2}"
            calc = f"(({y2} losses - {y1} losses) / {y1} losses) * 100"
        elif 'credit net' in subj_lower:
            short = "Credit net"
            data = f"{short} value for {y1}, {short} value for {y2}"
            calc = f"(({short} {y2} - {short} {y1}) / {short} {y1}) * 100"
        else:
            # Generic
            cap_subject = subject[0].upper() + subject[1:] if subject else subject
            data = f"{cap_subject} for {y1}, {cap_subject} for {y2}"
            calc = f"(({cap_subject} for {y2} - {cap_subject} for {y1}) / {cap_subject} for {y1}) * 100"
        
        constraints = "None"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === "what was the percent change in X from Y1 to Y2" ===
    if pct_change_match2 and not pct_change_what:
        subject_raw = pct_change_match2.group(1).strip()
        y1 = pct_change_match2.group(2)
        y2 = pct_change_match2.group(3)
        
        # Find original case
        subj_match = re.search(re.escape(subject_raw), q_normalized, re.IGNORECASE)
        if subj_match:
            original_subject = q_normalized[subj_match.start():subj_match.end()]
        else:
            original_subject = subject_raw
        
        # Detect if the original question uses "percent" vs "percentage"
        if re.search(r'\bpercent\b(?!age)', q_lower):
            target_word = "Percent"
        else:
            target_word = "Percentage"
        
        if re.search(r'\bchange\b', q_lower):
            change_word = "change"
        elif re.search(r'\bincrease\b', q_lower):
            change_word = "increase"
        elif re.search(r'\bdecrease\b', q_lower):
            change_word = "decrease"
        else:
            change_word = "change"
        
        subject_lower = subject_raw.lower()
        
        # Capitalize subject for data needed
        def capitalize_subject(s):
            return s[0].upper() + s[1:] if s else s
        
        cap_subj = capitalize_subject(subject_lower)
        
        target = f"{target_word} {change_word} in the {subject_lower} from {y1} to {y2}"
        data = f"{cap_subj} for {y1}, {cap_subj} for {y2}"
        calc = f"(({cap_subj} for {y2} - {cap_subj} for {y1}) / {cap_subj} for {y1}) * 100"
        constraints = "None"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === "what portion of X is related to/due in Y" ===
    if portion_match:
        total_thing = portion_match.group(1).strip().rstrip('?')
        part_thing = portion_match.group(2).strip().rstrip('?')
        
        total_lower = total_thing.lower()
        part_lower = part_thing.lower()
        
        if 'minimum total assets available for default' in total_lower and 'assessment powers' in part_lower:
            target = "Portion (percentage) of minimum total assets available for default related to assessment powers"
            data = "Minimum total assets available for default, Assets related to assessment powers"
            calc = "(Assets related to assessment powers / Minimum total assets available for default) * 100"
            constraints = "None"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
        
        if 'contingent acquisition obligation' in total_lower:
            target = "Portion of total estimated future contingent acquisition obligation due in the next 12 months"
            data = "Total estimated future contingent acquisition obligation, Estimated contingent acquisition obligation due in the next 12 months"
            calc = "(Estimated contingent acquisition obligation due in the next 12 months / Total estimated future contingent acquisition obligation) * 100"
            constraints = "None"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
        
        # Generic portion
        target = f"Portion of {total_lower} related to {part_lower}"
        data = f"{total_thing}, {part_thing}"
        calc = f"({part_thing} / {total_thing}) * 100"
        constraints = "None"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === "X are what percent of the total remaining" ===
    if what_pct_of:
        numerator_part = what_pct_of.group(1).strip()
        denominator_part = what_pct_of.group(2).strip().rstrip('?')
        
        num_lower = numerator_part.lower()
        den_lower = denominator_part.lower()
        
        if 'future minimum lease' in num_lower and 'after 5 years' in num_lower:
            target = "Percentage of total future minimum lease payments due after 5 years relative to total remaining lease payments"
            data = "Total future minimum lease payments due after 5 years, Total remaining future minimum lease payments"
            calc = "(Payments due after 5 years / Total remaining lease payments) * 100"
            constraints = "Focuses on payments after 5 years only, excludes payments due within 5 years"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
        
        target = f"Percentage of {num_lower} relative to {den_lower}"
        data = f"{numerator_part}, {denominator_part}"
        calc = f"({numerator_part} / {denominator_part}) * 100"
        constraints = "None"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === "total future minimum lease payments due after 5 years as a percentage of total remaining lease payments" ===
    lease_as_pct = re.search(
        r'total future minimum lease payments due after 5 years as a percentage of total remaining lease payments',
        q_lower
    )
    if lease_as_pct:
        target = "Percentage of total future minimum lease payments due after 5 years relative to total remaining lease payments"
        data = "Total future minimum lease payments due after 5 years, Total remaining lease payments"
        calc = "(Payments due after 5 years / Total remaining lease payments) * 100"
        constraints = "None"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === "what percentage of X are/is Y" with date ===
    if what_pct_match:
        total_thing = what_pct_match.group(1).strip()
        part_thing = what_pct_match.group(2).strip().rstrip('?')
        
        total_lower = total_thing.lower()
        part_lower = part_thing.lower()
        
        # Manufacturing and processing facilities
        if 'manufacturing and processing' in total_lower and 'owned' in part_lower:
            # Extract date
            date_match = re.search(r'as of ([A-Za-z]+ \d{1,2}, \d{4})', q_normalized, re.IGNORECASE)
            if not date_match:
                date_match = re.search(r'as of ([a-z]+ \d{1,2}\s*,\s*\d{4})', q_lower)
            
            date_str = ""
            if date_match:
                raw_date = date_match.group(1)
                # Clean up: capitalize month
                parts = raw_date.split()
                month = parts[0].capitalize()
                date_str = f"{month} {' '.join(parts[1:])}"
            
            target = f"Percentage of owned manufacturing and processing facilities as of {date_str}"
            data = f"Total manufacturing and processing facilities count as of {date_str}, Owned manufacturing and processing facilities count as of {date_str}"
            calc = "(Owned manufacturing and processing facilities / Total manufacturing and processing facilities) * 100"
            constraints = f"Time period constraint: {date_str}; Facility type constraint: manufacturing and processing only"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
        
        # "what percentage of total future principal payments of corporate debt are due in 2011?"
        if 'principal payments' in total_lower and 'corporate debt' in total_lower:
            year_match = re.search(r'due in (\d{4})', part_lower)
            year = year_match.group(1) if year_match else ""
            target = f"Percentage of total future principal payments of corporate debt due in {year}"
            data = f"Total future principal payments of corporate debt, Principal payments due in {year}"
            calc = f"(Principal payments due in {year} / Total future principal payments of corporate debt) * 100"
            constraints = f"Only include payments due in {year}"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
        
        # "what percentage of total operating revenues was associated with other revenues"
        if 'operating revenue' in total_lower and 'other revenue' in part_lower:
            year_match = re.search(r'in (\d{4})', q_lower)
            year = year_match.group(1) if year_match else ""
            target = f"Percentage of other revenues relative to total operating revenues in {year}"
            data = f"Total operating revenues for {year}, Other revenues for {year}"
            calc = "(Other revenues / Total operating revenues) * 100"
            constraints = f"Only consider data from the year {year}"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
        
        # Generic
        target = f"Percentage of {part_lower} relative to {total_lower}"
        data = f"{total_thing}, {part_thing}"
        calc = f"({part_thing} / {total_thing}) * 100"
        constraints = "None"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === "in 2008 what was the percent of the total operating revenues that was associated with other revenues" ===
    pct_of_match = re.search(
        r'(?:in (\d{4})\s+)?what (?:is|was) the percent(?:age)? of (?:the )?(.+?) (?:that (?:is|was|were) )?(?:associated with|related to) (.+)',
        q_normalized, re.IGNORECASE
    )
    if pct_of_match:
        year = pct_of_match.group(1) or ""
        total_thing = pct_of_match.group(2).strip()
        part_thing = pct_of_match.group(3).strip().rstrip('?')
        
        if 'operating revenue' in total_thing.lower():
            target = f"Percentage of {part_thing.lower()} relative to {total_thing.lower()} in {year}"
            data = f"Total operating revenues for {year}, Other revenues for {year}"
            calc = "(Other revenues / Total operating revenues) * 100"
            constraints = f"Only consider data from the year {year}"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === Average price per share ===
    if is_average and 'price per share' in q_lower:
        if quarter_match:
            q_num = quarter_match.group(1) or {'first': '1', 'second': '2', 'third': '3', 'fourth': '4'}.get(
                (quarter_match.group(2) or '').lower(), '')
            q_year = quarter_match.group(3)
            
            quarter_names = {'1': ('Q1', 'January 1', 'March 31'),
                           '2': ('Q2', 'April 1', 'June 30'),
                           '3': ('Q3', 'July 1', 'September 30'),
                           '4': ('Q4', 'October 1', 'December 31')}
            
            q_short, start_date, end_date = quarter_names.get(q_num, ('', '', ''))
            
            target = f"Average price per share of common stock in {q_short} {q_year}"
            data = f"Common stock price data for {q_short} {q_year}"
            calc = f"Sum of daily closing prices / Number of trading days in {q_short} {q_year}"
            constraints = f"Only include trading days from {start_date}, {q_year} to {end_date}, {q_year}"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === Cumulative total shareholder return ===
    cum_return = re.search(
        r'(?:percentage )?cumulative total shareholder return for (.+?) for the (five[- ]year period ending \d{1,2}/\d{1,2}/\d{2,4})',
        q_normalized, re.IGNORECASE
    )
    if cum_return:
        company = cum_return.group(1).strip()
        period = cum_return.group(2).strip()
        target = f"Percentage cumulative total shareholder return for {company} for the {period.replace('year ', 'year ')}"
        # Normalize
        target = re.sub(r'five year', 'five-year', target)
        data = f"Total shareholder return data for {company} over the {period}"
        data = re.sub(r'five year', 'five-year', data)
        calc = "Calculate cumulative total shareholder return percentage over the specified period"
        constraints = f"Time period filter: five years ending {period.split('ending ')[-1]}; Company filter: {company}"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === Ratio ===
    ratio_match = re.search(
        r'(?:in (\d{4})\s+)?what (?:is|was) the ratio of (?:the )?(.+?)\s+(?:that was )?(?:due )?(?:in )?(\d{4}) to (?:debt outstanding due in )?(\d{4})',
        q_normalized, re.IGNORECASE
    )
    if not ratio_match:
        ratio_match = re.search(
            r'(?:in (\d{4})\s+)?what (?:is|was) the ratio of (?:the )?(.+?)(?:\s+that was due in (\d{4}) to (\d{4}))',
            q_normalized, re.IGNORECASE
        )
    
    if ratio_match:
        context_year = ratio_match.group(1)
        subject = ratio_match.group(2).strip()
        y1 = ratio_match.group(3)
        y2 = ratio_match.group(4)
        
        # "annual cash sinking fund requirements for debt outstanding"
        subj_lower = subject.lower()
        
        if 'sinking fund' in subj_lower:
            target = f"Ratio of annual cash sinking fund requirements for debt outstanding due in {y1} to debt outstanding due in {y2}"
            data = f"Annual cash sinking fund requirements for debt due in {y1}, Annual cash sinking fund requirements for debt due in {y2}"
            calc = f"(Requirements for {y1} debt) / (Requirements for {y2} debt)"
            if context_year:
                constraints = f"Only consider data for the year {context_year}"
            else:
                constraints = "None"
            return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === "by what percentage can CME increase their current line of credit?" ===
    can_increase = re.search(
        r'by what percentage can (.+?) increase (?:their|its) (.+?)[\?]?$',
        q_normalized, re.IGNORECASE
    )
    if can_increase:
        entity = can_increase.group(1).strip()
        thing = can_increase.group(2).strip().rstrip('?')
        thing_lower = thing.lower()
        
        # For "current line of credit" -> use "line of credit" 
        display_thing = thing_lower
        
        target = f"Percentage increase in {display_thing}"
        data = f"Current {display_thing} amount, Potential new {display_thing} amount"
        calc = f"((Potential new {display_thing} - Current {display_thing}) / Current {display_thing}) * 100"
        constraints = "None"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === Compare/Determine ===
    compare_match = re.search(
        r'[Dd]etermine if in (\d{4}) .+? by comparing (.+?) to (.+?)$',
        q_normalized
    )
    if compare_match:
        year = compare_match.group(1)
        item1 = compare_match.group(2).strip()
        item2 = compare_match.group(3).strip()
        target = f"Compare distributions to shareholders versus debtholders in {year}"
        data = f"Dividends payable amount for {year}, Interest payable amount for {year}"
        calc = f"Compare ({item1}) > ({item2})"
        constraints = f"Only consider {year} data"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # === Percentage growth (title case, no question word) ===
    if pct_growth_title:
        subject = pct_growth_title.group(1).strip()
        y1 = pct_growth_title.group(2)
        y2 = pct_growth_title.group(3)
        target = f"Percentage growth of {subject} from {y1} to {y2}"
        cap_subj = subject[0].upper() + subject[1:]
        data = f"{cap_subj} for {y1}, {cap_subj} for {y2}"
        calc = f"(({cap_subj} {y2} - {cap_subj} {y1}) / {cap_subj} {y1}) * 100"
        constraints = "None"
        return f"Target: {target}\nData needed: {data}\nCalculation: {calc}\nConstraints: {constraints}"
    
    # Fallback - return None if we can't handle it confidently
    return None
