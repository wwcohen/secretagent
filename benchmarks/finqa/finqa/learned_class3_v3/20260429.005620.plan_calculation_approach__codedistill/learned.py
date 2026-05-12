"""Auto-generated code-distilled implementation for plan_calculation_approach."""

import re

def plan_calculation_approach(description):
    if not description or not isinstance(description, str):
        return None
    
    desc = description.strip()
    
    # Case 1: Percentage growth with formula like ((a - b) / b) * 100
    formula_match = re.search(r'\(\((\d+\.?\d*)\s*-\s*(\d+\.?\d*)\)\s*/\s*(\d+\.?\d*)\)\s*\*\s*100', desc)
    if formula_match and re.search(r'percentage growth', desc, re.IGNORECASE):
        val1 = formula_match.group(1)
        val2 = formula_match.group(2)
        year_match = re.search(r'from\s+(\d{4})\s+to\s+(\d{4})', desc, re.IGNORECASE)
        if year_match:
            year_from = year_match.group(1)
            year_to = year_match.group(2)
            return (f"Plan to calculate percentage growth from {year_from} to {year_to} by applying the percentage growth formula.\n"
                    f"Will use data points {val1} ({year_to} value) and {val2} ({year_from} value) from the provided table or context and perform subtraction, division, and multiplication operations.\n"
                    f"Need to consider ensuring the values are correctly identified for the specified years and that the calculation follows standard financial growth percentage methodology.")
    
    # Case 2: Ratio calculation
    ratio_match = re.search(r'[Cc]alculate\s+(?:the\s+)?ratio\s+of\s+(\d{4})\s+(.*?)\s+to\s+(\d{4})\s+(.*?)(?:\s+using\s+(.*))?$', desc)
    if ratio_match:
        year1 = ratio_match.group(1)
        item1 = ratio_match.group(2).rstrip()
        year2 = ratio_match.group(3)
        rest = ratio_match.group(4).rstrip()
        # Split rest to get item2 and source
        source_match = re.match(r'(.*?)\s+using\s+(.*)', rest)
        if source_match:
            item2 = source_match.group(1).rstrip()
            source = source_match.group(2).rstrip()
        else:
            item2 = rest
            source = "the table"
        
        # Use singular form for the first line (remove trailing 's' if plural)
        item_singular = re.sub(r'ss$', 's', item1.rstrip('s') + '' if not item1.endswith('s') else item1[:-1] if item1.endswith('ss') else item1[:-1])
        # Actually, let's just use item1 as-is but remove trailing 's' for singular
        item_base = item1
        if item_base.endswith('s') and not item_base.endswith('ss'):
            item_singular = item_base[:-1]
        else:
            item_singular = item_base
        
        return (f"Plan to calculate the ratio of {year1} {item_singular} to {year2} {item_singular} by dividing the {year1} value by the {year2} value.\n"
                f"Will use the {item_singular} values for {year1} and {year2} from {source} and perform the division operation ({year1}_value / {year2}_value).\n"
                f"Need to ensure the values are in the same unit and handle any missing data if present.")
    
    # Case 3: Percentage increase with dollar values
    pct_inc_match = re.search(r'[Cc]alculate\s+percentage increase\s+from\s+(.*)', desc)
    if pct_inc_match:
        rest_desc = pct_inc_match.group(1)
        dollar_matches = re.findall(r'\$[\d.]+\s+\w+', rest_desc)
        if len(dollar_matches) >= 2:
            return (f"Plan to calculate percentage increase from {rest_desc}.\n"
                    f"Will use current value ({dollar_matches[0]}) and potential value ({dollar_matches[1]}) from the input focus statement.\n"
                    f"Perform calculation: ((potential - current) / current) * 100 to get percentage increase.\n"
                    f"Need to ensure both values are in the same units (billions) and handle potential rounding for percentage result.")
    
    return None
