"""Auto-generated workflow-distilled implementation for answer_date_question.

Calls existing tools from ptools.
"""

from ptools import *

from datetime import datetime, timedelta
import re

def answer_date_question(question: str) -> str:
    """Workflow to answer date-related multiple choice questions."""
    
    # Strategy: Use LLM tools to parse the question, then compute with Python,
    # then match the option.
    
    # First, try to parse the question into components
    try:
        parsed = parse_question(question)
        # parsed should give us the reference date and the operation
    except:
        parsed = None
    
    # Use find_date_from_sentence to get the reference "today" date
    try:
        # Extract just the narrative part (before Options)
        parts = question.split("\nOptions:\n")
        narrative = parts[0] if parts else question
        options_text = parts[1] if len(parts) > 1 else ""
        
        today_date_str = find_date_from_sentence(narrative)
        
        # Try to identify the time difference/operation
        time_diff = identify_time_difference(narrative)
        
        # Parse today's date - try multiple formats
        today_date = None
        for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%y"]:
            try:
                today_date = datetime.strptime(today_date_str.strip(), fmt)
                break
            except:
                continue
        
        if today_date is None:
            # Try to extract date components with regex
            m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', today_date_str)
            if m:
                today_date = datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            else:
                m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', today_date_str)
                if m:
                    today_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        
        if today_date is not None:
            # Now apply the time difference
            # Try to use adjust_date_by_hours or compute manually
            result_date_str = adjust_date_by_hours(today_date_str, time_diff)
            
            # Parse result date
            result_date = None
            for fmt in ["%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    result_date = datetime.strptime(result_date_str.strip(), fmt)
                    break
                except:
                    continue
            if result_date is None:
                m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', result_date_str)
                if m:
                    result_date = datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            
            if result_date is not None:
                result_mm_dd_yyyy = result_date.strftime("%m/%d/%Y")
                
                # Extract options
                option_lines = re.findall(r'\(([A-Z])\)\s*(\S+)', options_text)
                
                for letter, date_val in option_lines:
                    if date_val.strip() == result_mm_dd_yyyy:
                        return f'({letter})'
                
                # If exact match failed, use select_closest_option
                result_letter = select_closest_option(result_mm_dd_yyyy, option_lines)
                if result_letter:
                    letter = extract_option_letter(result_letter)
                    if letter and re.match(r'\(?[A-Z]\)?', letter):
                        letter = letter.strip('()')
                        return f'({letter})'
    except:
        pass
    
    # Fallback: use the zero-shot approach
    raw = zeroshot_answer_date_question(question)
    letter = extract_option_letter(raw)
    # Normalize
    if letter:
        letter = letter.strip().strip('()')
        if len(letter) == 1 and letter.isalpha():
            return f'({letter.upper()})'
    
    # Last resort
    return letter if letter else None
