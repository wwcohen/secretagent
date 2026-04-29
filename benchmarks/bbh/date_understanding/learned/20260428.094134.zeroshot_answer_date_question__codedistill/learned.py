"""Auto-generated code-distilled implementation for zeroshot_answer_date_question."""

import re
from datetime import datetime, timedelta
import calendar

def zeroshot_answer_date_question(question_text):
    """Answer date-related multiple choice questions."""
    
    # Extract options
    options = re.findall(r'\(([A-F])\)\s*(\d{2}/\d{2}/\d{4})', question_text)
    if not options:
        return None
    
    # Extract the question part (before Options:)
    parts = question_text.split('Options:')
    if len(parts) < 2:
        return None
    question = parts[0].strip()
    
    # Try to determine the target date from the question
    target_date = extract_date_from_question(question)
    
    if target_date is None:
        return None
    
    # Format as MM/DD/YYYY
    target_str = target_date.strftime('%m/%d/%Y')
    
    # Find matching option
    for letter, date_str in options:
        if date_str == target_str:
            return f'({letter}) {date_str}'
    
    return None


def extract_date_from_question(question):
    """Extract/compute the target date from the question text."""
    
    month_names = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
        'oct': 10, 'nov': 11, 'dec': 12
    }
    
    question_lower = question.lower()
    
    # Try to find an explicit date first (MM/DD/YYYY)
    explicit_dates = re.findall(r'(\d{2}/\d{2}/\d{4})', question)
    
    # Try to find dates like "January 1, 2020" or "Jan 1, 2020"
    date_pattern1 = re.findall(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', question, re.IGNORECASE)
    
    # Determine base date
    base_date = None
    
    # Check for "last day of Month Year"
    last_day_match = re.search(r'last day of (\w+)\s+(\d{4})', question, re.IGNORECASE)
    if last_day_match:
        month_str = last_day_match.group(1).lower()
        year = int(last_day_match.group(2))
        if month_str in month_names:
            month = month_names[month_str]
            last_day = calendar.monthrange(year, month)[1]
            base_date = datetime(year, month, last_day)
    
    # Check for "first day of Month Year"
    if base_date is None:
        first_day_match = re.search(r'first day of (\w+)\s+(\d{4})', question, re.IGNORECASE)
        if first_day_match:
            month_str = first_day_match.group(1).lower()
            year = int(first_day_match.group(2))
            if month_str in month_names:
                month = month_names[month_str]
                base_date = datetime(year, month, 1)
    
    # Check for explicit MM/DD/YYYY in the question
    if base_date is None and explicit_dates:
        try:
            base_date = datetime.strptime(explicit_dates[0], '%m/%d/%Y')
        except ValueError:
            pass
    
    # Check for "Month DD, YYYY"
    if base_date is None and date_pattern1:
        for month_str, day_str, year_str in date_pattern1:
            if month_str.lower() in month_names:
                month = month_names[month_str.lower()]
                base_date = datetime(int(year_str), month, int(day_str))
                break
    
    if base_date is None:
        return None
    
    # Now check for modifiers (days ago, days from now, yesterday, tomorrow, etc.)
    target_date = apply_modifiers(question_lower, base_date)
    
    return target_date


def apply_modifiers(question_lower, base_date):
    """Apply temporal modifiers to the base date."""
    
    # Check for "X days ago" / "X days later" / "X days from now" / etc.
    
    word_to_num = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
        'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
        'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
        'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
        'hundred': 100
    }
    
    def parse_number(s):
        s = s.strip()
        try:
            return int(s)
        except ValueError:
            if s in word_to_num:
                return word_to_num[s]
            return None
    
    # "today is" / "date today" patterns - if question just asks "what is the date today"
    # with no further modifier, return base_date
    
    # Check for "yesterday"
    if 'yesterday' in question_lower:
        return base_date - timedelta(days=1)
    
    # Check for "tomorrow"
    if 'tomorrow' in question_lower:
        return base_date + timedelta(days=1)
    
    # Check for "X days ago"
    days_ago = re.search(r'(\w+)\s+days?\s+ago', question_lower)
    if days_ago:
        n = parse_number(days_ago.group(1))
        if n is not None:
            return base_date - timedelta(days=n)
    
    # Check for "X days later" or "X days from now" or "X days from today" or "after X days"
    days_later = re.search(r'(\w+)\s+days?\s+(?:later|from\s+now|from\s+today|after|hence)', question_lower)
    if days_later:
        n = parse_number(days_later.group(1))
        if n is not None:
            return base_date + timedelta(days=n)
    
    days_after = re.search(r'after\s+(\w+)\s+days?', question_lower)
    if days_after:
        n = parse_number(days_after.group(1))
        if n is not None:
            return base_date + timedelta(days=n)
    
    # Check for "X weeks ago"
    weeks_ago = re.search(r'(\w+)\s+weeks?\s+ago', question_lower)
    if weeks_ago:
        n = parse_number(weeks_ago.group(1))
        if n is not None:
            return base_date - timedelta(weeks=n)
    
    # Check for "X weeks later"
    weeks_later = re.search(r'(\w+)\s+weeks?\s+(?:later|from\s+now|from\s+today|after|hence)', question_lower)
    if weeks_later:
        n = parse_number(weeks_later.group(1))
        if n is not None:
            return base_date + timedelta(weeks=n)
    
    # Check for "X months ago" or "X months later"
    months_ago = re.search(r'(\w+)\s+months?\s+ago', question_lower)
    if months_ago:
        n = parse_number(months_ago.group(1))
        if n is not None:
            return add_months(base_date, -n)
    
    months_later = re.search(r'(\w+)\s+months?\s+(?:later|from\s+now|from\s+today|after|hence)', question_lower)
    if months_later:
        n = parse_number(months_later.group(1))
        if n is not None:
            return add_months(base_date, n)
    
    # Check for "X years ago" or "X years later"
    years_ago = re.search(r'(\w+)\s+years?\s+ago', question_lower)
    if years_ago:
        n = parse_number(years_ago.group(1))
        if n is not None:
            return add_months(base_date, -n * 12)
    
    years_later = re.search(r'(\w+)\s+years?\s+(?:later|from\s+now|from\s+today|after|hence)', question_lower)
    if years_later:
        n = parse_number(years_later.group(1))
        if n is not None:
            return add_months(base_date, n * 12)
    
    # Check for "the day before yesterday"
    if 'day before yesterday' in question_lower:
        return base_date - timedelta(days=2)
    
    # Check for "the day after tomorrow"
    if 'day after tomorrow' in question_lower:
        return base_date + timedelta(days=2)
    
    # No modifier found, return base date
    return base_date


def add_months(date, months):
    """Add months to a date."""
    month = date.month - 1 + months
    year = date.year + month // 12
    month = month % 12 + 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)
