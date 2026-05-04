"""Auto-generated workflow-distilled implementation for answer_date_question.

Calls existing tools from ptools.
"""

from ptools import *

import re
from datetime import datetime, timedelta

def answer_date_question(question: str) -> str:
    """Solve a date question by orchestrating sub-tools."""
    
    # Step 1: Use LLM to find the reference date from the sentence
    # Split question into the narrative and options
    parts = question.split("Options:")
    narrative = parts[0].strip() if parts else question
    
    # Extract the question part (what date is being asked for)
    # Find the actual question sentence
    question_match = re.search(r'What is the date (.+?) in MM/DD/YYYY\?', narrative)
    time_modifier = question_match.group(1).strip() if question_match else ""
    
    # Extract options
    options = re.findall(r'\(([A-Z])\)\s*(\d{2}/\d{2}/\d{4})', question)
    
    # Use LLM tool to find the reference date ("today") from the sentence
    reference_date_str = find_date_from_sentence(narrative)
    
    # Use LLM tool to identify the time difference described
    time_diff = identify_time_difference(narrative)
    
    # Try to parse the reference date
    target_date = None
    try:
        # Try to parse reference_date_str in various formats
        ref_date = None
        for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y", 
                     "%m/%d/%y", "%d/%m/%Y"]:
            try:
                ref_date = datetime.strptime(reference_date_str.strip(), fmt)
                break
            except ValueError:
                continue
        
        if ref_date is None:
            # Try extracting date from the string
            date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', reference_date_str)
            if date_match:
                m, d, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                ref_date = datetime(y, m, d)
            else:
                date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', reference_date_str)
                if date_match:
                    y, m, d = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                    ref_date = datetime(y, m, d)
        
        if ref_date is not None:
            # Try to compute the adjustment using the LLM-extracted time difference
            target_date_str = adjust_date_by_hours(ref_date.strftime("%m/%d/%Y"), time_diff)
            
            # Try to parse the target date
            for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"]:
                try:
                    target_date = datetime.strptime(target_date_str.strip(), fmt)
                    break
                except (ValueError, AttributeError):
                    continue
            
            if target_date is None:
                date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(target_date_str))
                if date_match:
                    m, d, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                    target_date = datetime(y, m, d)
    except Exception:
        pass
    
    if target_date is not None and options:
        target_str = target_date.strftime("%m/%d/%Y")
        # Direct match
        for letter, date_str in options:
            if date_str == target_str:
                return f'({letter})'
        # Use select_closest_option as fallback
        result = select_closest_option(target_str, options)
        return result
    
    # Fallback: use the zero-shot approach
    raw = zeroshot_answer_date_question(question)
    return extract_option_letter(raw)
