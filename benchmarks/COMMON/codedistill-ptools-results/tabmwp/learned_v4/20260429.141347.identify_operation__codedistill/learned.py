"""Auto-generated code-distilled implementation for identify_operation."""

import re

def identify_operation(question, table_info):
    q = question.lower()
    
    # Extract table structure info
    has_stem_leaf = 'stem' in table_info.lower() and 'leaf' in table_info.lower()
    has_frequency = 'frequency' in table_info.lower()
    has_price_qty = 'quantity demanded' in table_info.lower() or 'quantity supplied' in table_info.lower()
    has_xy = re.search(r'Columns:\s*x\s*\|\s*y', table_info) is not None
    
    # Check if table looks like a price list (item | $price format without "per pound" etc.)
    price_list = bool(re.search(r'\$[\d,.]+\s*\|', table_info)) and 'per pound' not in table_info.lower() and 'per lb' not in table_info.lower()
    
    # Probability questions - return 'lookup' generally but some need direct answers
    if 'probability' in q:
        # Check if it's a probability from a two-way table
        if re.search(r'Columns:\s*\|', table_info):
            # Two-way frequency table - might need direct computation
            # Check if answer should be a number
            return 'lookup'
        return 'lookup'
    
    # Shortage or surplus / comparison with price-quantity tables
    if has_price_qty or ('shortage' in q and 'surplus' in q):
        return 'comparison'
    
    # Linear or nonlinear
    if 'linear or nonlinear' in q:
        return 'comparison'
    
    # Fraction questions
    if 'what fraction' in q:
        if has_frequency or 'number of' in table_info.lower():
            # Could be average or fraction
            if 'respondent' in q or 'survey' in q:
                return 'average'
            return 'fraction'
        return 'fraction'
    
    # Mode
    if 'mode of the numbers' in q or 'what is the mode' in q:
        return 'mode'
    
    # Median
    if 'median' in q:
        return 'median'
    
    # Mean / average
    if 'mean of the numbers' in q or 'average' in q or 'mean number' in q or 'what is the mean' in q:
        return 'average'
    
    # Range
    if re.search(r'\brange\b', q) and 'randomly' not in q:
        return 'range'
    
    # Min/max
    if re.search(r'\bsmallest\b|\bminimum\b|\bfewest\b|\bleast\b', q) and not re.search(r'at least|how many.*least', q):
        return 'min'
    if re.search(r'\bmost\b|\blargest\b|\bgreatest\b|\bmaximum\b|\bhighest\b', q) and 'at most' not in q:
        if not re.search(r'how many.*most', q) and not has_frequency:
            return 'max'
    
    # "Does he/she have enough" -> comparison
    if 'does he have enough' in q or 'does she have enough' in q:
        return 'comparison'
    
    # "How much more" with price list tables that have specific item columns
    if re.search(r'how much more|how many more|how much less|how many fewer', q):
        if has_frequency or ('day' in table_info.lower() and 'number' in table_info.lower()):
            return 'difference'
        if price_list and not re.search(r'Columns:.*\|.*\|.*\|.*Rows', table_info):
            return 'comparison'
        return 'difference'
    
    # Rate of change -> difference
    if 'rate of change' in q:
        return 'difference'
    
    # Count questions (how many ... at least / fewer than / more than)
    if re.search(r'how many.*(at least|fewer than|more than|less than|between|but fewer)', q):
        return 'count'
    
    # "How many ... in total" / sum
    if re.search(r'how many.*in total|how many.*altogether|total number', q):
        return 'sum'
    
    # Frequency table with "how many customers/people" -> sum
    if has_frequency and re.search(r'how many', q):
        return 'sum'
    
    # Multiplication with table
    if re.search(r'each.*has.*\d+.*how many.*in \d+|each.*have.*\d+.*how many', q):
        return 'other'
    
    # "How much money will ... have left" -> other
    if 'have left' in q or 'left over' in q:
        return 'other'
    
    # "How much money does ... need to buy" with price list
    if 'need to buy' in q or 'how much does.*need' in q:
        return 'other'
    
    # Default lookup
    return 'lookup'
